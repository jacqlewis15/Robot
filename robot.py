
# Jacqueline Lewis
# robot.py


# This file contains the user interface and commands for the Bernhard Lab
# robotic fill system, utilizing a CNC machine and pumps controlled by the
# raspberry pi.


from Tkinter import *
import string
import serial
import time
import RPi.GPIO as GPIO
from multiprocessing import Process

####################################
# User Interface
####################################

def init(data):
	# drawing parameters
	data.margin = 10
	data.pump = ["",[""]*4,"",[""]*4,"",[""]*4,"",[""]*4]
	data.pumpheight = 600

	# for testing purposes, to save time
	data.pump[0] = "5"
	data.pump[1][0] = "0"
	data.pump[1][3] = "2.5"
	data.pump[2] = "solvent"
	data.pump[4] = "4"
	data.pump[5][0] = "2"
	data.pump[5][1] = "1"

	# editing parameters
	data.edit = [False,[False]*4,False,[False]*4,False,[False]*4,False,[False]*4]
	data.pipe = [False,[False]*4,False,[False]*4,False,[False]*4,False,[False]*4]
	data.editing = False
	data.time = 0
	data.error = ""

	# cnc machine parameters
	data.initial = (0,0,0)
	data.current = (0,0,0)
	data.limits = (220,160,45)

	# pump parameters, subject to change
	data.flowRate = [.5]*4
	data.mils = 1
	data.sigfig = 2
	data.fillNum = [0]*4

	# initialization of Raspberry Pi pins
	data.pumpPins = [(4,17,27),(22,5,6),(13,19,26),(23,24,25)]
	GPIO.setmode(GPIO.BCM)
	data.off = False
	data.on = True  
	for pin in data.pumpPins:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin,data.off)

	# chemicals to be pumped initialization
	data.amt = []
	for i in range(len(data.pump)//2):
		pumpArray = []
		for i in range(8):
			pumpArray.append([0]*12)
		data.amt.append(pumpArray)

# This function determines if a point is within certain bounds.
def within(x,y,corners):
	return (corners[0] < x < corners[2]) and (corners[1] < y < corners[3])

# This function enables editing of the concentrations.
def changeConc(data,i,j=None):
	if j == None:
		if (data.editing and data.edit[i]) or not data.editing:
			data.editing = True
			data.edit[i] = True
	else:
		if (data.editing and data.edit[i][j]) or not data.editing:
			data.editing = True
			data.edit[i][j] = True

# File I/O from 15-112
def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

# This function checks if the coordinates given are outside the allowable 
# limits.
def badCoords(coords,limits):
    for i in range(len(coords)):
        if coords[i] > limits[i]: return True
        if coords[i] < 0: return True
    return False

# This function sends movement instructions to the cnc machine and waits
# for them to be completed.
def move(data,coords): 

	axes = ["X","Y","Z"]
	contents = ""
	# ensures the given coordinates are valid to move to
	if badCoords(coords,data.limits):
		print("Point out of range")
	else:
		# writes the x,y,z movement instructions in g-code
		for i in range(len(coords)):
			dist = coords[i]-data.current[i]
			if dist == 0: continue
			contents += "$G\n"
			while(dist > 50):
				contents += ("G91G0%s%0.2f\n" % (axes[i],50.00))
				contents += "G90\n"
				contents += "$G\n"
				dist -= 50
			while(dist < -50):
				contents += ("G91G0%s%0.2f\n" % (axes[i],-50.00))
				contents += "G90\n"
				contents += "$G\n"
				dist += 50
			contents += ("G91G0%s%0.2f\n" % (axes[i],dist))
			contents += "G90\n"

		# Stream g-code to grbl
		for line in contents.split("\n"):
			l = line.strip() # Strip all EOL characters for consistency
			print 'Sending: ' + l,
			data.s.write(l + '\n') # Send g-code block to grbl
			grbl_out = data.s.readline() # Wait for grbl response with carriage return
			if l == "G90": data.s.readline()
			print ' : ' + grbl_out.strip()

		# updates the robot's location
		data.current = coords
		start = time.time()
		while(not query(data)):
			if time.time()-start > 100: 
				query(data,True)
				break
			continue

		# clears the grbl memory
		data.s.flushInput()
		data.s.flushOutput()

# This function activates the pumps.
def pump(data,idx):
	# determines where in the array the value for that well lies
	row = data.fillNum[idx]//12
	col = data.fillNum[idx] % 12
	if row % 2 == 1: col = 11 - col

	amt = data.amt[idx][row][col]
	tim = round(amt/data.flowRate[idx],data.sigfig)
	
	# debugging print statements that may actually be necessary
	print(tim)
	if tim == 0: return
	print("meow")

	# turns pumps on and off as necessary
	GPIO.output(data.pumpPins[idx][1], data.off)
	GPIO.output(data.pumpPins[idx][2], data.on)
	p = GPIO.PWM(data.pumpPins[idx][0], 60)
	start = time.time()
	p.start(40)
	while((time.time() - start) < tim): continue
	p.stop()

	GPIO.output(data.pumpPins[idx][0], data.off)
	GPIO.output(data.pumpPins[idx][2], data.off)

# This function checks if the cnc machine has finished its task.
def query(data,debug=False):
	data.s.write("?\n")
	response = data.s.readline()
	# debugging case
	if debug:
		print("Query: ")
		print(response)
	done = "Idle" in response
	# removes extraneous output line
	data.s.readline()
	return done

# This function operates all eligible pumps and moves to the pumping
# height, at the set location.
def dispense(data):
	# moves robot down
	move(data,(data.current[0],data.current[1],5))
	p = []
	# checks which pumps can be operated at their given positions
	if 62 <= data.current[0] <= 161: 
		print("Pump1")
		p.append((0,Process(target=pump,args=(data,0))))
	if 71 <= data.current[0] <= 170: 
		print("Pump2")
		p.append((1,Process(target=pump,args=(data,1))))
	if 80 <= data.current[0] <= 179: 
		print("Pump3")
		p.append((2,Process(target=pump,args=(data,2))))
	if 89 <= data.current[0] <= 188: 
		print("Pump4")
		p.append((3,Process(target=pump,args=(data,3))))
	data.s.flushInput()
	# runs pumps in parallel
	for (idx,motor) in p:
		motor.start()
	for (idx,motor) in p:
		motor.join()
	for (idx,motor) in p:
		data.fillNum[idx] += 1
	# moves robot up
	move(data,(data.current[0],data.current[1],20))
	
# This function moves the robot across a row and dispenses chemicals as needed.
def across(data,num,dirn):
	for i in range(14):
		dispense(data)
		move(data,(data.current[0]+dirn*9,data.current[1],data.current[2]))
	# fills last well
	dispense(data)
	# moves on y axis
	move(data,(data.current[0],data.current[1]+9*num,data.current[2]))

# This function moves the robot along the whole well setup and fills every
# well according to specs.
def path(data,mode,num):
	if mode == "hor":
		startx,starty = (62,33)
	# go to start
	move(data,(0,0,20))            ############## might need to run pump til liquid is ready to dispense
	move(data,(startx,starty,20))
	# fill rows
	for i in range(4//num): 
		across(data,num,1)
		across(data,num,-1) 

# This function determines how the concentration is being defined for this run.
def getBuildType(lst):
	patterns = [[0],[0,3],[0,1,3],[0,2,3],[0,1,2],[0,1,2,3],[0,1],[0,2]]
	for pattern in patterns:
		rest = [x for x in [0,1,2,3] if x not in pattern]
		yes = [isEmpty(lst[i]) for i in rest] + [not isEmpty(lst[i]) for i in pattern]
		if False not in yes: return pattern

# This function determines the amount to be dispensed from a pump if no gradient
# is desired.
def noGradient(data,idx):
	conc = float(data.pump[idx*2])
	goal = float(data.pump[idx*2+1][0])
	amt = goal*data.mils/conc
	pumpArray = []
	# all values of the array are equal
	for i in range(8):
		pumpArray.append([amt]*12)
	data.amt[idx] = pumpArray

# This function determines the amount to be dispensed from a pump if a 1D 
# gradient is desired.
def oneGradient(data,idx,buildType):
	if buildType == [0,3]: twoGradient(data,idx,buildType)
	if buildType == [0,1]: 
		# for x-axis gradients
		conc = float(data.pump[idx*2])
		low,high = float(data.pump[idx*2+1][0]),float(data.pump[idx*2+1][1])
		delta = (high-low)/11
		row = [low]
		# changes along row
		for i in range(11):
			row.append(row[-1]+delta)
		for i in range(len(row)):
			row[i] = round(row[i]*data.mils/conc,data.sigfig)
		pumpArray = []
		# each row is the same
		for i in range(8):
			pumpArray.append(row)
		data.amt[idx] = pumpArray
	if buildType == [0,2]:
		# for y-axis gradients
		conc = float(data.pump[idx*2])
		low,high = float(data.pump[idx*2+1][0]),float(data.pump[idx*2+1][2])
		delta = (high-low)/7
		col = [low]
		# changes along column
		for i in range(7):
			col.append(col[-1]+delta)
		for i in range(len(col)):
			col[i] = round(col[i]*data.mils/conc,data.sigfig)
		pumpArray = []
		# every column is the same
		for i in range(8):
			row = [col[i]]*12
			pumpArray.append(row)
		data.amt[idx] = pumpArray

# This function determines the amount to be dispensed from a pump if a 2D
# gradient is desired.
def twoGradient(data,idx,buildType):
	conc = float(data.pump[idx*2])
	corn = float(data.pump[idx*2+1][0])
	# the changes across x and y are dependent on build type
	if buildType == [0,1,2] or buildType == [0,1,2,3]:
		x,y = float(data.pump[idx*2+1][1]),float(data.pump[idx*2+1][2])
		deltax = (x-corn)/11
		deltay = (y-corn)/7
	if buildType == [0,1,3]:
		x,y = float(data.pump[idx*2+1][1]),float(data.pump[idx*2+1][3])
		deltax = (x-corn)/11
		deltay = (y-x)/7
	if buildType == [0,2,3]:
		y,x = float(data.pump[idx*2+1][2]),float(data.pump[idx*2+1][3])
		deltax = (x-y)/11
		deltay = (y-corn)/7
	if buildType == [0,3]:
		dif = float(data.pump[idx*2+1][3])-float(data.pump[idx*2+1][0])
		deltax = dif/22
		deltay = dif/14
	# build the concentration gradient
	col = [corn]
	for i in range(7):
		col.append(col[-1]+deltay)
	for i in range(len(col)):
		col[i] = round(col[i],data.sigfig)
	pumpArray = []
	for i in range(8):
		row = [col[i]]
		for i in range(11):
			row.append(row[-1]+deltax)
		for i in range(len(row)):
			row[i] = round(row[i]*data.mils/conc,data.sigfig)
		pumpArray.append(row)
	data.amt[idx] = pumpArray

# This function dispatches the different buildtypes to create the 
# concentration gradient.
def createArray(data,idx,mode=None):
	# the solvent amount depends on the other amounts added
	if mode == "solvent":
		for i in range(8):
			for j in range(12):
				total = 0
				for k in range(len(data.pump)//2):
					if k == idx: continue
					total += data.amt[k][i][j]
				data.amt[idx][i][j] = round((data.mils - total),data.sigfig)
	# determine build type and build array from that
	else:
		buildType = getBuildType(data.pump[idx*2+1])
		if len(buildType) == 1: noGradient(data,idx)
		if len(buildType) == 2: oneGradient(data,idx,buildType)
		if len(buildType) >= 3: twoGradient(data,idx,buildType)

# This function calculates the amounts to be added from each pump
# for each well.
def calcConcentrations(data):
	# calculate concentrations 
	for i in range(len(data.pump)//2):
		if data.pump[i*2] != "" and data.pump[i*2] != "solvent":
			createArray(data,i)
		if data.pump[i*2] == "solvent": solvent = i
	createArray(data,solvent,"solvent")

# This function fills the well system according to inputs in the UI.
def fill(data):
	# resets the filled index
	data.fillNum = [0]*4
	# calculates the amounts added in each well from each pump
	calcConcentrations(data)
	# opens communications with robot
	start = time.time()
	data.s = serial.Serial('/dev/ttyUSB0',115200)

	data.s.write("\r\n\r\n")
	time.sleep(2)   # Wait for grbl to initialize 
	data.s.flushInput()  # Flush startup text in serial input

	# move and fill along gradient
	path(data,"hor",1)

	# move back to start
	move(data,data.initial)
	# close communications with robot
	data.s.close()
	# print completion message
	data.error = ("Completed in %d minutes" % (round((time.time()-start)//60)))

# This function has the UI react to mouse clicks.
def mousePressed(event, data):
	index = event.x//(data.width//2)+2*(event.y//(data.pumpheight//2))
	# edits the concentration data in a particular cell
	if 0 <= index <= 3:
		left,right,top,bottom,bwidth,bheight = boundaries(data,index)
		if left < event.x < right:
			if top+bheight+data.margin < event.y < top+bheight*2+data.margin:
				# concentration of stock solution
				changeConc(data,index*2)
			else:
				idx = (event.x-left)//bwidth+2*((event.y-top-bheight*2-data.margin*2)//bheight)
				if 0 <= idx < 4:
					if within(event.x,event.y,getCorners(data,index,idx)):
						# concentration of gradient 
						index = index*2+1
						changeConc(data,index,idx)
	else:
		# presses the fill button
		left,right,top,bottom = fillButtonCorner(data)
		if (left < event.x < right) and (top < event.y < bottom):
			if checkConc(data):
				fill(data)

# This function if an object is or contains only the empty string.
def isEmpty(lst):
	for i in range(len(lst)):
		if lst[i] != "": return False
	return True

# This function checks if a 3D list contains a negative float.
def containsNeg(lst):
	for block in lst:
		for row in block:
			for elem in row:
				if float(elem) < 0: return True
	return False

# This function determines if the values entered for concentrations in the 
# UI are valid for computation and filling of the well system.
def checkConc(data):
	solvent = False
	for i in range(len(data.pump)//2):
		# a solvent must be present
		if data.pump[i*2] == "solvent": solvent = True
		# if a solution is being used, stock concentration must be known
		if ((not isEmpty(data.pump[i*2+1])) and ((data.pump[i*2] == "") 
			or (float(max(data.pump[i*2+1])) > float(data.pump[i*2])))):
			data.error = "Cannot reach desired concentration"
			return False
		# no partial entries allowed
		if (getBuildType(data.pump[i*2+1]) == None and 
			(data.pump[i*2] != "" and data.pump[i*2] != "solvent")): 
			data.error = "Invalid entry"
		# a fully labelled grid must be rectangular
		elif getBuildType(data.pump[i*2+1]) == [0,1,2,3]:
			if (((float(data.pump[i*2+1][1])-float(data.pump[i*2+1][0])) != 
				(float(data.pump[i*2+1][3])-float(data.pump[i*2+1][2]))) or
				((float(data.pump[i*2+1][2])-float(data.pump[i*2+1][0])) != 
				(float(data.pump[i*2+1][3])-float(data.pump[i*2+1][1])))):
				data.error = "Invalid entry"
		# ensures that no negative amounts are calculated
		if data.error == "":
			calcConcentrations(data)
			if containsNeg(data.amt): data.error = "Invalid combination"
	# returns whether the entries are error free
	if not solvent: data.error = "No solvent"
	return data.error == ""

# This function finds the corners of the fill button.
def fillButtonCorner(data):
	left,right,top,bottom,bwidth,bheight = boundaries(data,3)
	top = bottom + data.margin*2 + bheight
	bottom = top + bheight
	left = data.margin*2 + bwidth*1.5
	right = left + data.margin*2 + bwidth
	return left,right,top,bottom

# This function finds the location of a truth value in a non-regular
# 2D list of false values.
def getIndices(data):
	for i in range(len(data.edit)):
		if (type(data.edit[i]) != list) and data.edit[i]: 
			return i,None
		elif (type(data.edit[i]) == list):
			for j in range(len(data.edit[i])):
				if data.edit[i][j]: return i,j

# This function reacts the UI to input from a keyboard.
def keyPressed(event, data):
	data.error = ""
	if data.editing: 
		# allows the concentration gradient inputs to be edited
		i,j = getIndices(data)
		if event.keysym == "Return": # editing on/off
			if j == None: 
				data.edit[i] = data.editing = data.pipe[i] = False
			else: 
				data.edit[i][j] = data.editing = data.pipe[i][j] = False
		# allowable inputs
		elif event.keysym in str(range(10)):
			if j == None: data.pump[i] += event.keysym
			else: data.pump[i][j] += event.keysym
		elif event.char in "solvent":
			if j == None: data.pump[i] += event.char
		elif event.keysym == "period":
			if j == None: data.pump[i] += "."
			else: data.pump[i][j] += "."
		elif event.keysym == "BackSpace": # removes characters
			if j == None: data.pump[i] = data.pump[i][:-1]
			else: data.pump[i][j] = data.pump[i][j][:-1]
	# sends the robot back to the start, in case of failure
	if event.keysym == "Escape":
		for pin in data.pumpPins:
			GPIO.setup(pin, GPIO.OUT)
			GPIO.output(pin,data.off)
		data.s = serial.Serial('/dev/ttyUSB0',115200)

		data.s.write("\r\n\r\n")
		time.sleep(2)   # Wait for grbl to initialize 
		data.s.flushInput()  # Flush startup text in serial input
		move(data,(0,0,0))
		data.s.close()

# This function reacts to time passing.
def timerFired(data):
	# blinks cursor
	if (data.time % 5 == 0) and data.editing:
		i,j = getIndices(data)
		if j == None: data.pipe[i] = not data.pipe[i]
		else: data.pipe[i][j] = not data.pipe[i][j]
	data.time += 1

# This function finds the edges of the pump quadrant on the UI.
def boundaries(data,i):
	left = (i % 2)*data.width//2+data.margin
	right = (i % 2)*data.width//2+data.width//2-data.margin
	top = (i//2)*data.pumpheight//2+data.margin
	bottom = (i//2)*data.pumpheight//2+data.pumpheight//2-data.margin
	bwidth = (right-left-data.margin)//2
	bheight = (bottom-top-3*data.margin)//4
	return left,right,top,bottom,bwidth,bheight

# This function finds the corners of the buttons in the pump quadrant.
def getCorners(data,i,j):
	left,right,top,bottom,bwidth,bheight = boundaries(data,i)
	topx = left+(j % 2)*bwidth+(j % 2)*data.margin
	topy = top+(j//2)*bheight+(j//2)*data.margin+bheight*2+data.margin*2
	botx = topx+bwidth
	boty = topy+bheight
	return topx,topy,botx,boty

# This function translates from a true/false to a written cursor.
def pipe(data,i,j=None):
	if j == None:
		if data.pipe[i]: return "|"
		else: return " "
	elif data.pipe[i][j]: return "|"
	else: return " "

# This function writes the concentration data for a particular pump button.
def writeConc(canvas,data,i,j,topx,topy,bwidth,bheight):
	idx = i*2+1
	text = data.pump[idx][j] + pipe(data,idx,j)
	canvas.create_text(topx+bwidth//2,topy+bheight//2,text=text,font="Arial 20 bold")

# This function draws the rectangles and text for each pump on the UI.
def drawPump(canvas, data):
	numPumps = numCorners = 4
	for i in range(numPumps):
		left,right,top,bottom,bwidth,bheight = boundaries(data,i)
		for j in range(numCorners):
			# each corner of the grid in each pump gets a box and concentration
			topx,topy,botx,boty = getCorners(data,i,j)
			canvas.create_rectangle(topx,topy,botx,boty,fill="light yellow")
			writeConc(canvas,data,i,j,topx,topy,bwidth,bheight)
		mid = (right-left)//2+left
		# the stock concentration gets info
		canvas.create_text(mid,top+bheight//2,text="Pump "+str(i+1),font="Arial 20 bold")
		canvas.create_rectangle(left,top+bheight+data.margin,right,top+bheight*2+data.margin,fill="light yellow")
		canvas.create_text(left+5,top+bheight*1.5+data.margin,text="Concentration: "+data.pump[i*2]+pipe(data,i*2),anchor="w",font="Arial 20 bold")

# This function draws the fill button.
def drawStartButton(canvas,data):
	left,right,top,bottom = fillButtonCorner(data)
	canvas.create_rectangle(left,top,right,bottom,fill="light yellow")
	canvas.create_text(data.width//2,(bottom-top)//2+top,text="Fill",font="Arial 20 bold")
	canvas.create_text(data.width//2,top-data.margin-(bottom-top)//2,text=data.error,font="Arial 20 bold",fill="red")

# This function redraws the UI.
def redrawAll(canvas, data):
	canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="SpringGreen2")
	drawPump(canvas,data)
	drawStartButton(canvas,data)

####################################
# Run function, from 15-112
####################################

def run(width=300, height=300):
    def redrawAllWrapper(canvas, data):
        canvas.delete(ALL)
        redrawAll(canvas, data)
        canvas.update()    

    def mousePressedWrapper(event, canvas, data):
        mousePressed(event, data)
        redrawAllWrapper(canvas, data)

    def keyPressedWrapper(event, canvas, data):
        keyPressed(event, data)
        redrawAllWrapper(canvas, data)

    def timerFiredWrapper(canvas, data):
        timerFired(data)
        redrawAllWrapper(canvas, data)
        # pause, then call timerFired again
        canvas.after(data.timerDelay, timerFiredWrapper, canvas, data)
    # Set up data and call init
    class Struct(object): pass
    data = Struct()
    data.width = width
    data.height = height
    data.timerDelay = 100 # milliseconds
    init(data)
    # create the root and the canvas
    root = Tk()
    canvas = Canvas(root, width=data.width, height=data.height)
    canvas.pack()
    # set up events
    root.bind("<Button-1>", lambda event:
                            mousePressedWrapper(event, canvas, data))
    root.bind("<Key>", lambda event:
                            keyPressedWrapper(event, canvas, data))
    timerFiredWrapper(canvas, data)
    # and launch the app
    root.mainloop()  # blocks until window is closed
    GPIO.cleanup() # turns off all pins on pi

# runs the program
run(800, 750)

# # startup for headless pi
# class Struct(object): pass
# data = Struct()
# data.width = 800
# data.height = 750
# data.timerDelay = 100 # milliseconds

# init(data)

# fill(data)
# print("complete")
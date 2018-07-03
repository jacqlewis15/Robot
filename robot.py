

from Tkinter import *
import string
import serial
import time
import RPi.GPIO as GPIO
from multiprocessing import Process

def init(data):
	data.margin = 10
	data.pump = ["",[""]*4,"",[""]*4,"",[""]*4,"",[""]*4]

	data.pump[0] = "5"
	data.pump[1][0] = "0"
	data.pump[1][3] = "2.5"
	data.pump[2] = "solvent"
	data.pump[4] = "4"
	data.pump[5][0] = "2"
	data.pump[5][1] = "1"

	data.edit = [False,[False]*4,False,[False]*4,False,[False]*4,False,[False]*4]
	data.pipe = [False,[False]*4,False,[False]*4,False,[False]*4,False,[False]*4]
	data.editing = False
	data.time = 0
	data.pumpheight = 600
	data.error = ""

	data.initial = (0,0,0)
	data.current = (0,0,0)
	data.limits = (220,160,45)

	data.flowRate = [.5]*4
	data.mils = 1
	data.sigfig = 2
	data.fillNum = [0]*4

	data.pumpPins = [(4,17,27),(22,5,6),(13,19,26),(23,24,25)]
	GPIO.setmode(GPIO.BCM)
	data.off = False
	data.on = True  
	for pin in data.pumpPins:
		GPIO.setup(pin, GPIO.OUT)
		GPIO.output(pin,data.off)

	data.amt = []
	for i in range(len(data.pump)//2):
		pumpArray = []
		for i in range(8):
			pumpArray.append([0]*12)
		data.amt.append(pumpArray)

def within(x,y,corners):
	return (corners[0] < x < corners[2]) and (corners[1] < y < corners[3])

def changeConc(data,i,j=None):
	if j == None:
		if (data.editing and data.edit[i]) or not data.editing:
			data.editing = True
			data.edit[i] = True
	else:
		if (data.editing and data.edit[i][j]) or not data.editing:
			data.editing = True
			data.edit[i][j] = True

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def badCoords(coords,limits):
    for i in range(len(coords)):
        if coords[i] > limits[i]: return True
        if coords[i] < 0: return True
    return False

def move(data,coords): 
	# data.s.flushInput()
	axes = ["X","Y","Z"]
	contents = ""
	if badCoords(coords,data.limits):
	    print("Point out of range")
	else:
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
	    # writeFile('grbl.gcode',contents)

	    # # Open g-code file
	    # f = open('grbl.gcode','r');

	    # Stream g-code to grbl
	    for line in contents.split("\n"):
	        l = line.strip() # Strip all EOL characters for consistency
	        print 'Sending: ' + l,
	        data.s.write(l + '\n') # Send g-code block to grbl
	        grbl_out = data.s.readline() # Wait for grbl response with carriage return
	        if l == "G90": data.s.readline()
	        print ' : ' + grbl_out.strip()
	    # f.close()
	    data.current = coords
	    start = time.time()
	    while(not query(data)):
	    	if time.time()-start > 100: 
	    		query(data,True)
	    		break
	        continue
	    data.s.flushInput()
	    data.s.flushOutput()
	    # print("paused")
	    # data.s.flushInput()

def pump(data,idx):
	row = data.fillNum[idx]//12
	col = data.fillNum[idx] % 12
	if row % 2 == 1: col = 11 - col

	amt = data.amt[idx][row][col]
	tim = round(amt/data.flowRate[idx],data.sigfig)
	# if idx == 0: 
	# 	# print(amt)
	# 	print(tim)
	print(tim)
	if tim == 0: return
	print("meow")
	GPIO.output(data.pumpPins[idx][1], data.off)
	GPIO.output(data.pumpPins[idx][2], data.on)
	p = GPIO.PWM(data.pumpPins[idx][0], 60)
	start = time.time()
	p.start(40)
	while((time.time() - start) < tim): continue
	p.stop()

	GPIO.output(data.pumpPins[idx][0], data.off)
	GPIO.output(data.pumpPins[idx][2], data.off)

	# data.fillNum[idx] += 1
	print((idx,data.fillNum[idx]))

def query(data,debug=False):
	data.s.write("?\n")
	response = data.s.readline()
	# if not ("Idle" in response or "Run" in response):
	if debug:
		print("Query: ")
		print(response)
	done = "Idle" in response
	data.s.readline()
	return done

def dispense(data):
	move(data,(data.current[0],data.current[1],5))
	# run pump for desired time
	# while(not query(data)):
	# 	continue
	# print("done sleeping")
	p = []
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
	start = time.time()
	for (idx,motor) in p:
		motor.start()
	for (idx,motor) in p:
		motor.join()
	for (idx,motor) in p:
		data.fillNum[idx] += 1
	print(time.time() - start)
	# for i in range(4):
	# 	data.fillNum[i] += 1
	move(data,(data.current[0],data.current[1],20))
	
def across(data,num,dirn):
	for i in range(14):
		dispense(data)
		move(data,(data.current[0]+dirn*9,data.current[1],data.current[2]))
	dispense(data)
	move(data,(data.current[0],data.current[1]+9*num,data.current[2]))

def path(data,mode,num):
	if mode == "hor":
		startx,starty = (62,33)
	# go to start
	move(data,(0,0,20))
	# run pump so that liquid is ready to dispense
	move(data,(startx,starty,20))
	# dispense(data)
	for i in range(4//num): 
		across(data,num,1)
		across(data,num,-1)
	# across(data,num,1)
	# dispense   } repeat
	# move       }   

def getBuildType(lst):
	patterns = [[0],[0,3],[0,1,3],[0,2,3],[0,1,2],[0,1,2,3],[0,1],[0,2]]
	for pattern in patterns:
		rest = [x for x in [0,1,2,3] if x not in pattern]
		yes = [isEmpty(lst[i]) for i in rest] + [not isEmpty(lst[i]) for i in pattern]
		if False not in yes: return pattern

def noGradient(data,idx):
	conc = float(data.pump[idx*2])
	goal = float(data.pump[idx*2+1][0])
	amt = goal*data.mils/conc
	pumpArray = []
	for i in range(8):
		pumpArray.append([amt]*12)
	data.amt[idx] = pumpArray

def oneGradient(data,idx,buildType):
	if buildType == [0,3]: twoGradient(data,idx,buildType)
	if buildType == [0,1]: 
		conc = float(data.pump[idx*2])
		low,high = float(data.pump[idx*2+1][0]),float(data.pump[idx*2+1][1])
		delta = (high-low)/11
		row = [low]
		for i in range(11):
			row.append(row[-1]+delta)
		for i in range(len(row)):
			row[i] = round(row[i]*data.mils/conc,data.sigfig)
		pumpArray = []
		for i in range(8):
			pumpArray.append(row)
		data.amt[idx] = pumpArray
	if buildType == [0,2]:
		conc = float(data.pump[idx*2])
		low,high = float(data.pump[idx*2+1][0]),float(data.pump[idx*2+1][2])
		delta = (high-low)/7
		col = [low]
		for i in range(7):
			col.append(col[-1]+delta)
		for i in range(len(col)):
			col[i] = round(col[i]*data.mils/conc,data.sigfig)
		pumpArray = []
		for i in range(8):
			row = [col[i]]*12
			pumpArray.append(row)
		data.amt[idx] = pumpArray

def twoGradient(data,idx,buildType):
	conc = float(data.pump[idx*2])
	corn = float(data.pump[idx*2+1][0])
	if buildType == [0,1,2] or buildType == [0,1,2,3]:
		x,y = float(data.pump[idx*2+1][1]),float(data.pump[idx*2+1][2])
		# low,high = float(data.pump[idx*2+1][0]),float(data.pump[idx*2+1][2])
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
	col = [corn]
	for i in range(7):
		col.append(col[-1]+deltay)
	for i in range(len(col)):
		col[i] = round(col[i],data.sigfig)
	# high = float(data.pump[idx*2+1][1])
	# delta = (high-low)/7
	pumpArray = []
	for i in range(8):
		row = [col[i]]
		for i in range(11):
			row.append(row[-1]+deltax)
		for i in range(len(row)):
			row[i] = round(row[i]*data.mils/conc,data.sigfig)
		pumpArray.append(row)
	data.amt[idx] = pumpArray

def createArray(data,idx,mode=None):
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

def calcConcentrations(data):
	# calculate concentrations 
	for i in range(len(data.pump)//2):
		if data.pump[i*2] != "" and data.pump[i*2] != "solvent":
			createArray(data,i)
		if data.pump[i*2] == "solvent": solvent = i
	createArray(data,solvent,"solvent")

def fill(data):
	data.fillNum = [0]*4
	calcConcentrations(data)
	print(data.amt[0])
	# move and fill along gradient
	start = time.time()
	data.s = serial.Serial('/dev/ttyUSB0',115200)

	data.s.write("\r\n\r\n")
	time.sleep(2)   # Wait for grbl to initialize 
	data.s.flushInput()  # Flush startup text in serial input

	path(data,"hor",1)

	move(data,data.initial)
	# time.sleep(2)
	# while(not query(data)):
	# 	continue
	# print("done sleeping")
	data.s.close()

	data.error = ("Completed in %d minutes" % (round((time.time()-start)//60)))

	# return to stop and print completion message

def mousePressed(event, data):
	index = event.x//(data.width//2)+2*(event.y//(data.pumpheight//2))
	if 0 <= index <= 3:
		left,right,top,bottom,bwidth,bheight = boundaries(data,index)
		if left < event.x < right:
			if top+bheight+data.margin < event.y < top+bheight*2+data.margin:
				changeConc(data,index*2)
			else:
				idx = (event.x-left)//bwidth+2*((event.y-top-bheight*2-data.margin*2)//bheight)
				if 0 <= idx < 4:
					if within(event.x,event.y,getCorners(data,index,idx)):
						index = index*2+1
						changeConc(data,index,idx)
	else:
		left,right,top,bottom = fillButtonCorner(data)
		if (left < event.x < right) and (top < event.y < bottom):
			if checkConc(data):
				fill(data)

def isEmpty(lst):
	for i in range(len(lst)):
		if lst[i] != "": return False
	return True

def containsNeg(lst):
	for block in lst:
		for row in block:
			for elem in row:
				if float(elem) < 0: return True
	return False

def checkConc(data):
	solvent = False
	for i in range(len(data.pump)//2):
		if data.pump[i*2] == "solvent": solvent = True
		if ((not isEmpty(data.pump[i*2+1])) and ((data.pump[i*2] == "") 
			or (float(max(data.pump[i*2+1])) > float(data.pump[i*2])))):
			data.error = "Cannot reach desired concentration"
			return False
		if (getBuildType(data.pump[i*2+1]) == None and 
			(data.pump[i*2] != "" and data.pump[i*2] != "solvent")): 
			data.error = "Invalid entry"
		elif getBuildType(data.pump[i*2+1]) == [0,1,2,3]:
			if (((float(data.pump[i*2+1][1])-float(data.pump[i*2+1][0])) != 
				(float(data.pump[i*2+1][3])-float(data.pump[i*2+1][2]))) or
				((float(data.pump[i*2+1][2])-float(data.pump[i*2+1][0])) != 
				(float(data.pump[i*2+1][3])-float(data.pump[i*2+1][1])))):
				data.error = "Invalid entry"
		if data.error == "":
			calcConcentrations(data)
			if containsNeg(data.amt): data.error = "Invalid combination"
	if not solvent: data.error = "No solvent"
	return data.error == ""

def fillButtonCorner(data):
	left,right,top,bottom,bwidth,bheight = boundaries(data,3)
	top = bottom + data.margin*2 + bheight
	bottom = top + bheight
	left = data.margin*2 + bwidth*1.5
	right = left + data.margin*2 + bwidth
	return left,right,top,bottom

def getIndices(data):
	for i in range(len(data.edit)):
		if (type(data.edit[i]) != list) and data.edit[i]: 
			return i,None
		elif (type(data.edit[i]) == list):
			for j in range(len(data.edit[i])):
				if data.edit[i][j]: return i,j

def keyPressed(event, data):

	data.error = ""
	if data.editing: 
		i,j = getIndices(data)
		if event.keysym == "Return":
			if j == None: 
				data.edit[i] = data.editing = data.pipe[i] = False
			else: 
				data.edit[i][j] = data.editing = data.pipe[i][j] = False
		elif event.keysym in str(range(10)):
			if j == None: data.pump[i] += event.keysym
			else: data.pump[i][j] += event.keysym
		elif event.char in "solvent":
			if j == None: data.pump[i] += event.char
		elif event.keysym == "period":
			if j == None: data.pump[i] += "."
			else: data.pump[i][j] += "."
		elif event.keysym == "BackSpace":
			if j == None: data.pump[i] = data.pump[i][:-1]
			else: data.pump[i][j] = data.pump[i][j][:-1]
	if event.keysym == "Escape":
		print("meow")
		for pin in data.pumpPins:
			GPIO.setup(pin, GPIO.OUT)
			GPIO.output(pin,data.off)
		data.s = serial.Serial('/dev/ttyUSB0',115200)

		data.s.write("\r\n\r\n")
		time.sleep(2)   # Wait for grbl to initialize 
		data.s.flushInput()  # Flush startup text in serial input
		move(data,(0,0,0))
		data.s.close()

def timerFired(data):
	if (data.time % 5 == 0) and data.editing:
		i,j = getIndices(data)
		if j == None: data.pipe[i] = not data.pipe[i]
		else: data.pipe[i][j] = not data.pipe[i][j]
	data.time += 1

def boundaries(data,i):
	left = (i % 2)*data.width//2+data.margin
	right = (i % 2)*data.width//2+data.width//2-data.margin
	top = (i//2)*data.pumpheight//2+data.margin
	bottom = (i//2)*data.pumpheight//2+data.pumpheight//2-data.margin
	bwidth = (right-left-data.margin)//2
	bheight = (bottom-top-3*data.margin)//4
	return left,right,top,bottom,bwidth,bheight

def getCorners(data,i,j):
	left,right,top,bottom,bwidth,bheight = boundaries(data,i)
	topx = left+(j % 2)*bwidth+(j % 2)*data.margin
	topy = top+(j//2)*bheight+(j//2)*data.margin+bheight*2+data.margin*2
	botx = topx+bwidth
	boty = topy+bheight
	return topx,topy,botx,boty

def pipe(data,i,j=None):
	if j == None:
		if data.pipe[i]: return "|"
		else: return " "
	elif data.pipe[i][j]: return "|"
	else: return " "

def writeConc(canvas,data,i,j,topx,topy,bwidth,bheight):
	idx = i*2+1
	text = data.pump[idx][j] + pipe(data,idx,j)
	canvas.create_text(topx+bwidth//2,topy+bheight//2,text=text,font="Arial 20 bold")

def drawPump(canvas, data):
	numPumps = numCorners = 4
	for i in range(numPumps):
		left,right,top,bottom,bwidth,bheight = boundaries(data,i)
		for j in range(numCorners):
			topx,topy,botx,boty = getCorners(data,i,j)
			canvas.create_rectangle(topx,topy,botx,boty,fill="light yellow")
			writeConc(canvas,data,i,j,topx,topy,bwidth,bheight)
		mid = (right-left)//2+left
		canvas.create_text(mid,top+bheight//2,text="Pump "+str(i+1),font="Arial 20 bold")
		canvas.create_rectangle(left,top+bheight+data.margin,right,top+bheight*2+data.margin,fill="light yellow")
		canvas.create_text(left+5,top+bheight*1.5+data.margin,text="Concentration: "+data.pump[i*2]+pipe(data,i*2),anchor="w",font="Arial 20 bold")

def drawStartButton(canvas,data):
	left,right,top,bottom = fillButtonCorner(data)
	canvas.create_rectangle(left,top,right,bottom,fill="light yellow")
	canvas.create_text(data.width//2,(bottom-top)//2+top,text="Fill",font="Arial 20 bold")
	canvas.create_text(data.width//2,top-data.margin-(bottom-top)//2,text=data.error,font="Arial 20 bold",fill="red")

def redrawAll(canvas, data):
	canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="SpringGreen2")
	drawPump(canvas,data)
	drawStartButton(canvas,data)

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
    GPIO.cleanup()

run(800, 750)
# class Struct(object): pass
# data = Struct()
# data.width = 800
# data.height = 750
# data.timerDelay = 100 # milliseconds

# init(data)

# fill(data)
# print("complete")
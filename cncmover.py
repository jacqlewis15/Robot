
import serial
import time

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def badCoords(coords,limits):
    for i in range(len(coords)):
        if coords[i] > limits[i]: return True
        if coords[i] < 0: return True
    return False



# Open grbl serial port
s = serial.Serial('/dev/ttyUSB0',115200)

# Wake up grbl
s.write("\r\n\r\n")
time.sleep(2)   # Wait for grbl to initialize 
s.flushInput()  # Flush startup text in serial input

initial = (0,0,0)
current = (0,0,0)
limits = (235,160,45)
axes = ["X","Y","Z"]

def move(current,coords):
    contents = ""
    if badCoords(coords,limits):
        print("Point out of range")
        return(current)
    else:
        for i in range(len(coords)):
            dist = coords[i]-current[i]
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
            s.write(l + '\n') # Send g-code block to grbl
            grbl_out = s.readline() # Wait for grbl response with carriage return
            print ' : ' + grbl_out.strip()
        # f.close()
        return coords

# Wait here until grbl is finished to close serial port and file.
while(True):
    raw = raw_input("Enter (x,y,z) coords or press Enter to exit\n")
    if len(raw) <= 0: break
    x,y,z = raw.split(",")
    x = x[1:]
    z = z[:-1]
    coords = float(x),float(y),float(z)
    current = move(current,coords)

move(current,initial)

# Close file and serial port
s.close()


import RPi.GPIO as GPIO
import time

pins = [4,17,27]
GPIO.setmode(GPIO.BCM)
GPIO.setup(pins[0], GPIO.OUT)
GPIO.setup(pins[1], GPIO.OUT)
GPIO.setup(pins[2], GPIO.OUT)
off = False
on = True

GPIO.output(pins[1], off)

pulser = 4
GPIO.output(pins[2], on)

p = GPIO.PWM(pulser, 60)

p.start(40)
time.sleep(2)
p.stop()  

GPIO.cleanup()

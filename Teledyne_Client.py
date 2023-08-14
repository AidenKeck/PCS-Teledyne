from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE
import time
from ocs.ocs_client import OCSClient
#Establishing serial connection with Arduino
connection = Serial(port='/dev/ttyACM1', baudrate=9600, timeout=.1)


#Establishing serial connection with pressure gauge. 
press_client = OCSClient('Tele1')
press_client.acq.start()

response = press_client.acq.status()

totalStepSize = 0
exit = 0
oldPressure = response.session.get('data')['fields']['pressure']
timeDifference = 1
hold = 0
check = True
timer = time.perf_counter()

endPressure = float(input("What is the desired end pressure?"))
endPressure = min(endPressure, 850)
endPressure = max(endPressure, 270)

pumpDirection = int(input("Are you cooling down or warming up? Enter 1 for cooling, 2 for warming: "))

inc = int(input("Preferred initial step size: "))

increment = int(input("How much do you want to increase each step?: "))

maxStep = int(input("What do you want the maximum step to be?: "))

strinc = str(inc)
strincrement = str(increment)
strmaxStep = str(maxStep)

connection.write(('3' + '\n').encode())
time.sleep(1)
connection.write((strinc + '\n').encode())
time.sleep(1)
connection.write((strincrement + '\n').encode())
time.sleep(1)
connection.write((strmaxStep + '\n').encode())
time.sleep(1)
connection.write(('1' + '\n').encode())


#Gets pressure and related timestamp from session object in OCS framework and uses those values to find ost recent pressure rate
while(exit == 0):
	time.sleep(8)
	response = press_client.acq.status()
	oldPressure = response.session.get('data')['fields']['pressure']
	startTime = response.session.get('data')['fields']['timestamp']
	time.sleep(1)
	response = press_client.acq.status()
	currentPressure = response.session.get('data')['fields']['pressure']
	endTime = response.session.get('data')['fields']['timestamp']
	

# Taking an input pressure and time since last measurement; calculating rate
	print("Current pressure is: " + str(currentPressure))

	timeElapsed = endTime - startTime
	if timeElapsed == 0:
	    continue
	else:
	    rate = (currentPressure-oldPressure)/timeElapsed
	
	
#Comparing current pressure to end pressure set by user to tell program to stop. 
	if pumpDirection == 1:
		if(currentPressure <= 200):
			exit = 1
			break
	elif pumpDirection == 2:
		if(currentPressure >= 970):
			exit = 1
			break
#check is used to limit the total amount of times stepper motor can turn, that way it doesn't try to open fully open needlevalve
	if (currentPressure >= endPressure and pumpDirection == 2) or (currentPressure <= endPressure and pumpDirection == 1):
		check = False
#Tell the motor to speed up if the rate dips below 1mbar/10sec, or close if rate is above 15 mbar/10sec
	print(f"Current rate is: {rate:.3} mb/sec")
	if(pumpDirection == 2 and rate < 0) or (pumpDirection == 1 and rate > 0 and time.perf_counter() - timer >= 180) and check:
		print("The pressure is going other direction. Check DR state.")
		exit = 2
	elif(abs(rate) < 0.8 and check):
		hold = int(1.8 * (inc-10))
		print(f"The rate has dropped below the threshold. Making adjustment of {hold} degrees")
		time.sleep(1)
		connection.write(('1' + '\n').encode())
		if inc <= maxStep:
			inc += increment
		totalStepSize += inc
	elif(abs(rate) > 0.125):
		print("The rate can potentially damage items in DR. Please act if this message appears again")
		hold = int(1.8 * (inc-10))
		print(f"Making closing adjustment of {hold} degrees")
		time.sleep(1)
		totalStepSize -= (inc - 10)
		connection.write(('2' + '\n').encode())
	elif(check):
		print("The rate is above the threshold. Check again soon.")

#If it exited properly, chooses to close the needle-valve
if exit == 1:
	print("Proceeding to close the needle valve.")
	val = str(totalStepSize)
	if totalStepSize > 3 and totalStepSize <= 30000:
		connection.write((val + '\n').encode())
	else:
		print("totalStepsize too big, make things into long")
	time.sleep(1)

connection.close()

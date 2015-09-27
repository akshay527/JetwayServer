import time
import sys
import subprocess
import os
import MySQLdb
import ConfigParser

# Main script for starting, stopping, and checking the status of measurements
# Requires "Machines.txt" file in the current directory

configParser = ConfigParser.RawConfigParser()   
configFilePath = r'.dbconfig'
configParser.read(configFilePath)

db = MySQLdb.connect(host='feature.isri.cmu.edu', # your host, usually localhost
                     user=configParser.get('db','user'), # your username
                      passwd=configParser.get('db','passwd'), # your password
                      db='measurement') # name of the data base
cur = db.cursor() 

seriesIdCache = {}

command = None
userInput = False
testlist = ['kmeans', 'particle_filter', 'srad', 'hotspot', 'nw']

def validSeries(seriesname):
	for name in testlist:
		if name in seriesname:
			return True
	return False

def ex(cmd):
	subprocess.call(cmd, shell=True)

def getSeriesId(seriesname):
	global cur
        if seriesname not in seriesIdCache:
                cur.execute('select SeriesID from Series where name="'+seriesname+'"')
                r=cur.fetchone()
                if r==None:
                        print "Series "+seriesname+" not found in measurement database. Quitting."
                        sys.exit(1)
                seriesIdCache[seriesname]=r[0]
        return seriesIdCache[seriesname]

def copyFiles(seriesname):
	for name in seriesname:
		ex('ansible all -u feature -m copy -a "src=~/misc/Master/sac-compile-'+name+'.sh dest=~/energy/sac-compile.sh mode=777"')
		ex('ansible all -u feature -m copy -a "src=~/misc/Master/sac-run-'+name+'.sh dest=~/energy/sac-run.sh mode=777"')

def printStatus():
	global cur
	print "\nSeries Name : Remaining Todos\n"
        sql = "SELECT * FROM Series"
        cur.execute(sql)
        for row in cur:
                seriesname = str(row[2])
                sql = "SELECT Count(*) FROM Todos WHERE SeriesID = " + str(getSeriesId(seriesname))
                cur.execute(sql)
                numTodos = (cur.fetchone())[0]
                print seriesname + " : " + str(numTodos)
	print "\nNumber of threads attached to MySQL database: "
	no_tests_in_progress()

def startTests(seriesname=""):
	global userInput
	if userInput:
		printStatus()	
		seriesname = str(raw_input("\nSeries Name? "))
	copyFiles(seriesname)
	with open("Machines.txt") as f:
		for fline in f:
			ex("ssh " + fline.strip() + ' "bash /home/feature/energy/sac.sh start ' + seriesname + '" &')

def stopTests():
	with open("Machines.txt") as f:
                for fline in f:
                        ex("ssh " + fline.strip() + ' "bash /home/feature/energy/sac.sh stop" &')
	
	time.sleep(15)

def no_tests_in_progress():
	sql = "SHOW STATUS WHERE `variable_name` = 'Threads_connected'"
	global cur
	cur.execute(sql)
	x = cur.fetchone()
	print int(x[1])
	return int(x[1]) <= 5

def checkTodos():
	global userInput
	global cur
	userInput = False
	sql = "SELECT * FROM Series"
	cur.execute(sql)
	L = []
	for row in cur:
		L.append(row)
	for row in L:
		seriesname = row[2]
		sql = "SELECT Count(*) FROM Todos WHERE SeriesID = " + str(getSeriesId(seriesname))
		cur.execute(sql)
		numTodos = (cur.fetchone())[0]
		if int(numTodos) > 0 and no_tests_in_progress() and validSeries(seriesname):
			startTests(seriesname)
			print "\nTests have now begun for " + seriesname + '\n'
			break

def main():
	global userInput
	global command

	print "MASTER SCRIPT COMMANDS"
	print "1: Check measurement progress"
	print "2: Start measurements"
	print "3: Stop measurements"
	print "4: Quit\n"

	if len(sys.argv) == 1:
		userInput = True
		command = str(raw_input("What would you like to do? (1 - 4) " ))

	if command == '1':
		printStatus()

	if command == '2':
		if no_tests_in_progress():
			startTests()
			time.sleep(5)
			print "\n\nDone."
		else:
			print "\n\nTests already in progress"

	if command == '3':
		stopTests()

	if command != '4':
		print "\n\n"
		main()

if __name__ == "__main__":
	try:
		print "\n\nNOTE: Please make sure all machines in Machines.txt have SSH key access setup.\n File path modification may be necessary based on test infrastructure setup\n\n"
        	main()
		cur.close()
		db.close()
	except Exception, e:
		pass


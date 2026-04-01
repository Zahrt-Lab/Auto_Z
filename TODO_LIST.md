# Big TODO List in order

1) Write test cases of all equipment used in project_dead_mans_fingers to ensure there is no logic issues and equipment hardware is working to help with troubleshooting.

2) Currently there are lot of serial connections that are the same logic, with connect, drain, etc, next priority is to move these utils in their own scripts and functions to make it cleaner.

3) Currently with the status button, this causes a lot errors if two commands run at the same time, threading is being used currently but async should be used in the future to prevent any of this conflict.

4) The methods directory is a bit messy right now to get everything to work, need to clean this up and make it easier to add new instruments for future users. 

5) A lot of the pump logic is the same, can maybe include some general purpose math for all our test ases to ensure everything is working. 

6) Directories are getting crowded should be cleaned up and organized to make it cleaner for people. 
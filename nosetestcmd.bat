@echo off
echo Exclude tests with @attr('DST') because they fail on Windows 
echo with a 1 hour difference due to Daylight Savings Time (I think)
echo Exclude @attr('universalMultiLevel') code (in development)
echo Exclude @attr('tbd') tests currently broken
echo.
echo on
nosetests  -a "!DST","!universalMultiLevel","!tbd" -s -v -v elodie.tests


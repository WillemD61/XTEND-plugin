# XTEND-plugin

This is a Domoticz plugin for collection of data from an Intergas Xtend heatpump unit.

Once installed and activated, the plugin will create 52 Domoticz devices (in plugin version 1.0.0) and then collect data from the Xtend indoor unit and store the data on the Domoticz devices. The Domoticz devices can be seen via the Domoticz GUI and used for further processing into a Domoticz or Dashticz dashboard (that is a planned future publication here on Github).

This plugin does NOT communicate data back to the Xtend. It does NOT allow any control of the heatpump. It only collects information. For anyone wanting to control for example the thermostat setpoint, the Intergas InComfort LAN2RF Gateway hardware plugin is recommended (provided you have the Intergas Gateway installed of course) or any other Opentherm communication device.

# WIFI connection

The plugin uses the WIFI connection of the Xtend indoor unit. The WIFI connection needs to be activated by pressing the button on the Xtend indoor unit after which the LED will start flashing purple. The Domoticz server needs to be connected to the WIFI connection of the Xtend (see user manual). I use a Raspberry Pi as Domoticz server, which is connected with a LAN/Ethernet cable to my central home router so the WIFI connection of the Raspberry Pi is then available for the connection to the Xtend.

The WIFI connection of the Xtend needs to be kept active, otherwise it will close automatically after 30 minutes. Normally the plugin will keep the connection active but as an additional assurance, just in case Domoticz or the plugin crashes, it is recommended to install an additional data query in the system crontab, using the following line:
*/5 * * * * curl 10.20.30.1/api/stats/values?fields=6573
This will request the ambient temperature every 5 minutes and therefore keep the connection open even if Domoticz fails. For even more assurance this query could be done from a separate server, i.e. different hardware from the Domoticz server.

# Sensor data 

This plugin is based on the excellent work done by Dennis Schoutsen (https://github.com/DSchoutsen/HA_connection_Xtend) and Thomas van Tilburg (https://github.com/thomasvt1/xtend-bridge) for integration of the Xtend with Home Assistant. I have used their info about sensor codes and their dashboard code to determine which sensor info to collect. As result, using the Domoticz devices you get more or less the same data as availabe from the Xtend directly (when you connect your PC directly to the Xtend, open a webbrowser and look at the summary or statistics pages). 

Note that not all sensors might give useful information in your particular case. For example in my own case my older Intergas boiler does not provide the supply and return temperature. I still have included these sensors in the data collection to keep the plugin general purpose. You can deactivate such sensors in Domoticz if desired. Also I could not identify the correct keys for some sensors from the Xtend interface, for example the crank and pan heater info, so those have been left out (for now).

I started data collection myself on 25-06-2025. Future versions of the plugin might use different or more sensors and Domoticz devices, depending on experience gained and feedback received.

# Domoticz code

The plugin uses the newer DomoticzEx extended plugin framework. It contains one workaround for a Domoticz bug related to kWh devices, as also shown in the Python code. Also, for energy usage (in kWh) it uses the power info (in Watts) from the Xtend and lets Domoticz calculate the energy in kWh. Personally, I also use a Homewizard WIFI kWh device for power and energy measurement. This is separate from the plugin.

# Prerequisite for installation 

1) Make sure Python is installed on your system with the json and requests libraries. 
2) Make sure to backup your system before installing. The plugin works in my environment, but is provided as-is without any warranty.

# Installation instructions

1) Login to the Domoticz server and obtain a command line.
2) Change to the plugin directory with "cd domoticz/plugins".
3) Create a new plugin directory with "mkdir XTEND-plugin".
4) Change to the new directory with "cd XTEND-plugin".
5) Copy the file plugin.py from this Github repository into the XTEND-plugin directory.
6) Restart Domoticz with "sudo service domoticz restart".
7) Once restarted, select the Intergas Xtend plugin via the Domoticz Setup-Hardware menu, give it a name, select a polling interval and confirm.
8) It will now create the new devices and after the first polling interval, it will start collecting the data.
9) Check the Domoticz log file for any issues and progress. 

Step 3 to 5 above can be replaced with "git clone https://github.com/WillemD61/XTEND-plugin" 

# Future development

Expected: Create either a Dashticz dashboard or a Domoticz dashboard (using roomplan/floorplan).




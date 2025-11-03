# Intergas Xtend plugin, developed using Basic Python Plugin Example as provided by GizMoCuz
#
# author WillemD61
# version 1.0.1
# - removed double use of code 65c1 (device 9 and 15 in version 1.0.0.)
# - added description for Boiler status values (843a)
# - added error handling in case XTEND wifi connection not active
# - added code for generating default Dashticz config.js for dashboard
# version 1.0.2
# - added shorter polling intervals
# - replaced datapoint 8e38 by 7ee6, boiler temp
# version 1.03
# - adapted for maximum Domoticz heartbeat 30 seconds
# version 1.04
# - added explicit conversion to integer when assigning nValue (without raised error in Domoticz 2025.2)
# version 1.05
# - data validation on invalid responses added
# - sensor codes aligned with Xtend screen codes
#     5077=energy generated replaced by 503e=heatpump energy generated
#     7e81 instead of 623c for CH return temperature
#     62d1 instead of 6573 for outside temperature
#     7ed3 instead of 844c for water pressure
#     7e31 instead of 8e8f for boiler setpoint temperature
#     *** note that code references in description field off the devices need to be adapted manually  ***
# - renamed devices
#     "Burner status" renamed to "Heat demand boiler"
#     "Heatdemand status" renamed to "Heat demand HP"
# - additional sensors added
#     5088 Boiler energy generated
#     b2bc Boiler Flame
#     f9f2 Status flags

"""
<plugin key="IntergasXtend" name="Intergas Xtend heatpump" author="WillemD61" version="1.0.5" >
    <description>
        <h2>Intergas Xtend heatpump</h2><br/>
        This plugin uses the API on the Intergas Xtend WIFI connection to get the values of a large numbers of parameters<br/>
        and then load these values onto Domoticz devices. Devices will be created if they don't exists already.<br/><br/>
        The Xtend WIFI connection needs to be active, indicated by a flashing purple LED light on the indoor unit.<br/>
        (activation is done by pressing the button on the indoor unit).<br/>
        Also the Domoticz server needs to be connected already to the active Xtend WIFI connection.<br/><br/>
        A large number of devices is created, similar to the parameters shown in the Intergas web interface.<br/>
        Also the Home Assistant integrations by DSchoutsen and thomasvt1 published on Github were used as input.<br/><br/>
        Configuration options...
    </description>
    <params>
        <param field="Mode1" label="Polling Interval" width="150px">
            <options>
                <option label="10 seconds" value="10" />
                <option label="20 seconds" value="20" />
                <option label="30 seconds" value="30" default="true" /> # maximum domoticz heartbeat time is 30 seconds
                <option label="1 minute" value="60" />
                <option label="2 minutes" value="120" />
                <option label="3 minutes" value="180" />
                <option label="4 minutes" value="240" />
                <option label="5 minutes" value="300" />
            </options>
        </param>
    </params>
</plugin>
"""
import DomoticzEx as Domoticz
import json,requests   # make sure these are available in your system environment
from requests.exceptions import Timeout

# A dictionary to list all parameters to be retrieved from Xtend and to define the Domoticz devices to hold them.
# Temperature sensor are listed first but order of sensors is not important for the functioning of the program
# Make sure Unit numbers are incremental and make sure fieldcodes are correct!!!!
# currently only english name is provided, can be extended with other languages
# availability of some sensors values will depend on your boiler type and year

# Dictionary structure is as follows: fieldcode : [ Unit, Type, Subtype, Switchtype, OptionsList{}, Multiplier, Name ],

DEVSLIST={
# 80,5,0 : temperature devices
    "79b3":  [ 1, 80, 5, 0, {}, 0.01, "Room temp"],
    "7921":  [ 2, 80, 5, 0, {}, 0.01, "Target room temp"],
    "62d1":  [ 3, 80, 5, 0, {}, 0.01, "Outside temp"],
    "6280":  [ 4, 80, 5, 0, {}, 0.01, "HP return temp"],
    "62e7":  [ 5, 80, 5, 0, {}, 0.01, "HP supply temp "],
    "62ed":  [ 6, 80, 5, 0, {}, 0.01, "HP setpoint temp"],
    "65d9":  [ 7, 80, 5, 0, {}, 0.01, "Exhaust gas temp"],
    "6505":  [ 8, 80, 5, 0, {}, 0.01, "Suction line gas temp"],
    "47e0":  [ 9, 243,19, 0, {}, 1, "Software version"], # added to replace unused device in version 1.0.0.
    "6c26":  [ 10, 80, 5, 0, {}, 0.01, "Condensor gas temp"],
    "6ceb":  [ 11, 80, 5, 0, {}, 0.01, "Condensor liquid temp"],
    "6cfb":  [ 12, 80, 5, 0, {}, 0.01, "Suction line overheat temp"],
    "6c33":  [ 13, 80, 5, 0, {}, 0.01, "Discharge overheat temp"],
    "6c53":  [ 14, 80, 5, 0, {}, 0.01, "Subcooling temp"],
    "65c1":  [ 15, 80, 5, 0, {}, 0.01, "Coil temp"],
    "7ee6":  [ 16, 80, 5, 0, {}, 0.01, "Boiler temp"], # replacing 8e38 because no longer available in firmware 0.86
    "7e31":  [ 17, 80, 5, 0, {}, 0.01, "Boiler CH setpoint temp"],
    "625b":  [ 18, 80, 5, 0, {}, 0.01, "Boiler CH supply temp"],
    "7e81":  [ 19, 80, 5, 0, {}, 0.01, "Boiler CH return temp"],
    "8ecb":  [ 20, 80, 5, 0, {}, 0.01, "Boiler DHW max temp"],
    "8edb":  [ 21, 80, 5, 0, {}, 0.01, "Boiler DHW actual temp"],
# 243,9,0 : pressure devices
    "7ed3":  [ 22, 243, 9, 0, {}, 0.01, "CH water pressure"],
    "6579":  [ 23, 243, 9, 0, {}, 0.01, "HP suction pressure"],
    "65b0":  [ 24, 243, 9, 0, {}, 0.01, "HP discharge gas pressure"],
# 243,30,0 : flow devices
    "8e7f":  [ 25, 243, 30, 0, {}, 0.01, "Boiler DHW flow"],
    "629c":  [ 26, 243, 30, 0, {}, 0.01, "HP CH flow"],
# 243,7,0 : fan device
    "6c8a":  [ 27, 243, 7, 0, {}, 1, "Fan speed"], # note multiplier 1
# 243,6,0 : percentage device
    "848e":  [ 28, 243, 6, 0, {}, 0.01, "Boiler modulation target"],
    "84d1":  [ 29, 243, 6, 0, {}, 0.01, "Boiler modulation level"],
    "62cb":  [ 30, 243, 6, 0, {}, 0.01, "Pump level"],
# 243,31,0 : custom device
    "65a7":  [ 31, 243, 31, 0, {'Custom':'1;Hz'}, 0.01, "Compressor frequency"], # note options field sets the label for custom device
    "71a7":  [ 32, 243, 31, 0, {'Custom':'1;HR'}, 1, "HP poweron"],
# 113,0,3 : counter device
    "6ac5":  [ 33, 113, 0, 3, {'ValueQuantity':'Custom','ValueUnits':'HR'}, 1, "HP runtime"],
    "8ef9":  [ 34, 113, 0, 3, {'ValueQuantity':'Custom','ValueUnits':'HR'}, 1, "Boiler CH runtime"],
    "8e37":  [ 35, 113, 0, 3, {'ValueQuantity':'Custom','ValueUnits':'HR'}, 1, "Boiler DHW runtime"],
    "6a8e":  [ 36, 113, 0, 3, {}, 1, "HP Compressor starts"],
    "7160":  [ 37, 113, 0, 3, {}, 1, "HP power cycles"],
    "6a53":  [ 38, 113, 0, 3, {}, 1, "HP defrost cycles"],
    "8e00":  [ 39, 113, 0, 3, {}, 1, "Boiler starts"],
    "6a8d":  [ 40, 113, 0, 3, {}, 1, "Boiler DHW starts"],
    "8e18":  [ 41, 113, 0, 3, {}, 1, "Boiler flame loss count"],
    "712c":  [ 42, 113, 0, 3, {}, 1, "Boiler ignition fail count"],
# 243,29,0 or 4: kwh device
    "50f2":  [ 43, 243, 29, 0, {'EnergyMeterMode': '1'}, 1, "HP energy usage"],
    "503e":  [ 44, 243, 29, 4, {'EnergyMeterMode': '1'}, 1, "HP energy generated"],
# 243,31,0 : custom device
    "5041":  [ 45, 243, 31, 0, {}, 0.1, "COP"],
# 243,19,0 : text device
    "7e7a":  [ 46, 243, 19, 0, {}, 1, "Heat demand Boiler"],
    "7e51":  [ 47, 243, 19, 0, {}, 1, "Heat demand HP"],
    "657e":  [ 48, 243, 19, 0, {}, 1, "Operation mode"],
    "6578":  [ 49, 243, 19, 0, {}, 1, "Working mode"],
    "777d":  [ 50, 243, 19, 0, {}, 1, "Heatpump mode"],
    "77dd":  [ 51, 243, 19, 0, {}, 1, "System status"],
    "843a":  [ 52, 243, 19, 0, {}, 1, "Boiler status"],
# devices added in later versions
    "5088":  [ 53, 243, 29, 4, {'EnergyMeterMode': '1'}, 1, "Boiler energy generated"],
    "b2bc":  [ 54, 243, 19, 0, {}, 1, "Boiler flame"],
    "f9f2":  [ 55, 243, 19, 0, {}, 1, "Status flags"],
}

# define the url to get the Xtend field values
XtendIP="http://10.20.30.1"  # the IP address of the Xtend indoor unit after activation by pressing the button
XtendAPI="/api/stats/values?fields=" # the API line to request field values
APIFieldsString=""  # the list of field values to be requested in the url, based on the dictionary above
for Dev in DEVSLIST:
    APIFieldsString+=Dev
    APIFieldsString+=","
APIurl=XtendIP+XtendAPI+APIFieldsString


class XtendPlugin:
    enabled = False
    def __init__(self):
        return

    def onStart(self):
        Domoticz.Log("onStart called with parameters")
        for elem in Parameters:
            Domoticz.Log(str(elem)+" "+str(Parameters[elem]))
        if int(Parameters["Mode1"])<=30:
            Domoticz.Heartbeat(int(Parameters["Mode1"]))
            self.heartbeatWaits=0
        else:
            Domoticz.Heartbeat(30)
            self.heartbeatWaits=int(int(Parameters["Mode1"])/30 - 1)
        self.heartbeatCounter=0
        #Domoticz.Log("HBwaits: "+str(self.heartbeatWaits)+", HBcounter: "+str(self.heartbeatCounter))
        self.Hwid=Parameters['HardwareID']
        # cycle through device list and create any non-existing devices when the plugin/domoticz is started
        for Dev in DEVSLIST:
            Unit=DEVSLIST[Dev][0]
            DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
            Type=DEVSLIST[Dev][1]
            Subtype=DEVSLIST[Dev][2]
            Switchtype=DEVSLIST[Dev][3]
            Options=DEVSLIST[Dev][4]
            Name="XTEND: "+DEVSLIST[Dev][6]
            Description="Xtend field code :"+Dev
            if DeviceID not in Devices:
                Domoticz.Status(f"Creating device for Field {Dev} ...")
                if ((Type==243) and (Subtype==29)):
                    # below code puts an initial svalue on the kwh device and then changes the type to "computed". This is to work around a BUG in Domoticz for computed kwh devices. See issue 6194 on Github.
                    Domoticz.Unit(DeviceID=DeviceID,Unit=Unit, Name=Name, Type=Type, Subtype=Subtype, Switchtype=Switchtype, Options={}, Used=1, Description=Description).Create()
                    Devices[DeviceID].Units[Unit].sValue="0;0"
                    Devices[DeviceID].Units[Unit].Update()
                    Devices[DeviceID].Units[Unit].Options=Options
                    Devices[DeviceID].Units[Unit].Update(UpdateOptions=True)
                else:
                    Domoticz.Unit(DeviceID=DeviceID,Unit=Unit, Name=Name, Type=Type, Subtype=Subtype, Switchtype=Switchtype, Options=Options, Used=1, Description=Description).Create()
        for Dev in DEVSLIST:
            Domoticz.Log("DEVSLIST "+str(DEVSLIST[Dev][0])+DEVSLIST[Dev][6])
        self.createCONFIGJS()


    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, DeviceID, Unit, Command, Level, Color):
        Domoticz.Log("onCommand called for Device " + str(DeviceID) + " Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")
        #Domoticz.Log("HBwaits: "+str(self.heartbeatWaits)+", HBcounter: "+str(self.heartbeatCounter))
        # skip one or more heartbeats if polling interval > 30 seconds
        if self.heartbeatWaits==self.heartbeatCounter:
            self.getXtendData()
            self.heartbeatCounter=0
        else:
            self.heartbeatCounter+=1

    def getXtendData(self):
        Domoticz.Log("getXtendData called")
        self.Hwid=Parameters['HardwareID']
        try:
            response=requests.get(APIurl, timeout=5)
            if response.status_code==200:
                responseJson=response.json()
                #Domoticz.Log(responseJson["stats"])
                for Dev in DEVSLIST:
                    type=DEVSLIST[Dev][1]
                    subtype=DEVSLIST[Dev][2]
                    Unit=DEVSLIST[Dev][0]
                    DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                    #print(str(responseJson["stats"][Dev]))
                    if ((Devices[DeviceID].Units[Unit].Used==1) and (str(responseJson["stats"][Dev])!="32767")): # invalid value will not processed
                        if ((type==80) or # temperature device
                            (type==113) or # counter device
                            ((type==243) and (subtype==9)) or # pressure device
                            ((type==243) and (subtype==30)) or # waterflow device
                            ((type==243) and (subtype==7)) or # fan device
                            ((type==243) and (subtype==6)) or # percentage device
                            ((type==243) and (subtype==31)) # custom device
                                                    ):
                            multiplier=DEVSLIST[Dev][5]
                            if multiplier==1:
                                fieldValue=round(float(multiplier*responseJson["stats"][Dev]),0)
                            else:
                                fieldValue=round(float(multiplier*responseJson["stats"][Dev]),1)
                            Devices[DeviceID].Units[Unit].nValue=int(fieldValue)
                            Devices[DeviceID].Units[Unit].sValue=str(fieldValue)
                            Devices[DeviceID].Units[Unit].Update()

                        if ((type==243) and (subtype==29)): # kwh device
                            fieldValue=responseJson["stats"][Dev]
                            if fieldValue>=0 and fieldValue<10000 : # only valid values will be processed
                                Devices[DeviceID].Units[Unit].nValue=0
                                Devices[DeviceID].Units[Unit].sValue=str(fieldValue)+";1" # watts are supplied, kwh are calculated by Domoticz.
                                Devices[DeviceID].Units[Unit].Update()
                        if ((type==243) and (subtype==19)): # text device
                            fieldValue=responseJson["stats"][Dev]
                            if Dev=="47e0":
                                Devices[DeviceID].Units[Unit].nValue=0
                                fieldText=fieldValue
                            else:
                                Devices[DeviceID].Units[Unit].nValue=int(fieldValue)
                                fieldText=str(fieldValue)
                            if Dev=='777d':
                                if fieldValue==0: fieldText="DHW"
                                elif fieldValue==1: fieldText="HEATING"
                                elif fieldValue==2:  fieldText="COOLING"
                                elif fieldValue==253: fieldText="PUMPDOWN"
                                elif fieldValue==254: fieldText="OFF"
                                elif fieldValue==255: fieldText="UNDEFINED"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='77dd':
                                if fieldValue==0: fieldText="MONITOR_LOCKOUT"
                                elif fieldValue==1: fieldText="PUMP_VENTING"
                                elif fieldValue==2:  fieldText="SERVICE"
                                elif fieldValue==3: fieldText="DEFROST"
                                elif fieldValue==4: fieldText="DHW"
                                elif fieldValue==5: fieldText="ROOMHEATING_COMFORT"
                                elif fieldValue==6: fieldText="ROOMHEATING_ECO"
                                elif fieldValue==7: fieldText="ROOMCOOLING"
                                elif fieldValue==8: fieldText="DHW_HEATEXCHANGE"
                                elif fieldValue==9: fieldText="FLOORHEATINGPROTOCOL"
                                elif fieldValue==12: fieldText="ANTIFREEZE"
                                elif fieldValue==13: fieldText="PUMP_MAINTENANCE"
                                elif fieldValue==14: fieldText="IDLE"
                                elif fieldValue==255: fieldText="NO_TASK"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='6578':
                                if fieldValue==0: fieldText="COOLING"
                                elif fieldValue==1: fieldText="HEATING"
                                elif fieldValue==2:  fieldText="DEFROSTING"
                                elif fieldValue==3: fieldText="PUMPDOWN"
                                elif fieldValue==255: fieldText="UNDEFINED"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='657e':
                                if fieldValue==0: fieldText="DHW"
                                elif fieldValue==1: fieldText="HEATING"
                                elif fieldValue==2:  fieldText="COOLING"
                                elif fieldValue==253: fieldText="PUMPDOWN"
                                elif fieldValue==254: fieldText="OFF"
                                elif fieldValue==255: fieldText="UNDEFINED"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='7e51':
                                if fieldValue==0: fieldText="OPENTHERM"
                                elif fieldValue==15: fieldText="BOILER_EXT"
                                elif fieldValue==24:  fieldText="FROST"
                                elif fieldValue==37:  fieldText="CH_RF"
                                elif fieldValue==51:  fieldText="DHW_INT"
                                elif fieldValue==85:  fieldText="SENSORTEST"
                                elif fieldValue==86:  fieldText="COMMISSIONING"
                                elif fieldValue==87:  fieldText="CRANKHEATING"
                                elif fieldValue==102:  fieldText="CH"
                                elif fieldValue==103:  fieldText="CH_WAIT"
                                elif fieldValue==104:  fieldText="DEFROSTING"
                                elif fieldValue==117:  fieldText="STARTING_COOLING"
                                elif fieldValue==118:  fieldText="COOLING"
                                elif fieldValue==119:  fieldText="COOLING_WAIT"
                                elif fieldValue==126:  fieldText="STANDBY"
                                elif fieldValue==127:  fieldText="OFF"
                                elif fieldValue==153:  fieldText="POSTRUN_BOILER"
                                elif fieldValue==170:  fieldText="SERVICE"
                                elif fieldValue==189:  fieldText="POSTRUN_COOLING"
                                elif fieldValue==204:  fieldText="DHW"
                                elif fieldValue==205:  fieldText="DHW_HRECO"
                                elif fieldValue==230:  fieldText="STARTING_CH"
                                elif fieldValue==231:  fieldText="POSTRUN_CH"
                                elif fieldValue==240:  fieldText="BOILER_INT"
                                elif fieldValue==255:  fieldText="HEATUP"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='7e7a':
                                if fieldValue==0: fieldText="STARTUP"
                                elif fieldValue==1: fieldText="INTERPURGE"
                                elif fieldValue==2:  fieldText="POSTPURGE"
                                elif fieldValue==4: fieldText="PREPURGE"
                                elif fieldValue==8: fieldText="IGNITION"
                                elif fieldValue==16: fieldText="WAITING"
                                elif fieldValue==32: fieldText="RUNNING"
                                elif fieldValue==64: fieldText="REST"
                                elif fieldValue==128: fieldText="LOCKOUT"
                                else: fieldText="Unknown, value: "+str(fieldValue)
                            if Dev=='843a':
                                if fieldValue==0: fieldText="OFF"
                                elif fieldValue==10: fieldText="GAS HEATING"
                                elif fieldValue==12: fieldText="DHW"
                                else: fieldText="Unknown, value: "+str(fieldValue)

                            Devices[DeviceID].Units[Unit].sValue=fieldText
                            Devices[DeviceID].Units[Unit].Update()
            else:
                raise Exception
        except Timeout:
            Domoticz.Error("Timeout on getting Xtend data. Check connection.")
        except:
            Domoticz.Error("No proper Xtend data received. Check connection.")


    def createCONFIGJS(self): # create a default CONFIG.js file for a Dashticz dashboard
        try:
            fileHandle=open("DASHTICZCONFIG.js","w")
            # file heading
            print("var config = {}",file=fileHandle)
            print("config['language'] = 'en_US'; //or: nl_NL, en_US, de_DE, fr_FR, hu_HU, it_IT, pt_PT, sv_SV",file=fileHandle)
            print("config['domoticz_ip'] = 'http://xxx.xxx.xxx.xxx:port';",file=fileHandle)
            print("config['domoticz_refresh'] = '5';",file=fileHandle)
            print("config['dashticz_refresh'] = '60';",file=fileHandle)
            # blocks
            print("//Definition of blocks",file=fileHandle)
            print("blocks = {}",file=fileHandle)
            for Dev in DEVSLIST:
                Unit=DEVSLIST[Dev][0]
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    print("blocks["+"\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'] = {",file=fileHandle)
                else:
                    print("blocks["+str(Devices[DeviceID].Units[Unit].ID)+"] = {",file=fileHandle)

                print("    last_update:false,",file=fileHandle)
                print("    width: 12",file=fileHandle)
                print("}",file=fileHandle)
            # columns
            print("//Definition of columns",file=fileHandle)
            print("columns = {}",file=fileHandle)

            print("columns[\"xtendsummary\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [1,2,3,47,49,48,51,50,9]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)
                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)

            print("columns[\"xtendtoday\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [22,32,33,36,37,38,43,44,45]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)
                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)

            print("columns[\"xtendactual1\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [6,5,4,7,8,10,11,12,13]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)
                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)

            print("columns[\"xtendactual2\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [14,15,23,24,27,30,26,31,55]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)
                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)

            print("columns[\"boileractual1\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [34,35,39,40,52,46,41,42,53]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)
                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)


            print("columns[\"boileractual2\"] = {",file=fileHandle)
            print("    blocks : [",end=" ",file=fileHandle)
            for Unit in [16,17,18,19,28,29,20,21,25,54]:
                DeviceID="{:04x}{:04x}".format(self.Hwid,Unit)
                if (Devices[DeviceID].Units[Unit].Type==113 or (Devices[DeviceID].Units[Unit].Type==243 and Devices[DeviceID].Units[Unit].SubType==29)):
                    DomoticzID="\'"+str(Devices[DeviceID].Units[Unit].ID)+"_1\'"
                else:
                    DomoticzID=str(Devices[DeviceID].Units[Unit].ID)

                print(DomoticzID,end=",",file=fileHandle)
            print("],",file=fileHandle)
            print("    width: 2",file=fileHandle)
            print("}",file=fileHandle)


            # screens
            print("//Definition of screens",file=fileHandle)
            print("screens = {}",file=fileHandle)
            print("screens[1] = {",file=fileHandle)  # change this screen number if you already have existing dashticz screens
            print("    columns: [\"xtendsummary\",\"xtendtoday\",\"xtendactual1\",\"xtendactual2\",\"boileractual1\",\"boileractual2\"]",file=fileHandle)
            print("}",file=fileHandle)
            fileHandle.close()
        except:
            Domoticz.Error("ERROR: problem creating default Dashticz CONFIG.js")
            fileHandle.close()

global _plugin
_plugin = XtendPlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(DeviceID, Unit, Command, Level, Color):
    global _plugin
    _plugin.onCommand(DeviceID, Unit, Command, Level, Color)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Domoticz.Debug("Device ID:       '" + str(Device.DeviceID) + "'")
        Domoticz.Debug("--->Unit Count:      '" + str(len(Device.Units)) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Domoticz.Debug("--->Unit:           " + str(UnitNo))
            Domoticz.Debug("--->Unit Name:     '" + Unit.Name + "'")
            Domoticz.Debug("--->Unit nValue:    " + str(Unit.nValue))
            Domoticz.Debug("--->Unit sValue:   '" + Unit.sValue + "'")
            Domoticz.Debug("--->Unit LastLevel: " + str(Unit.LastLevel))
    return

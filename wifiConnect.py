import network
 
def connect():
  
  #ssid = "BOLT!-8D33"
  #password =  "385D63A5"
  
  ssid = "MyASUS"
  password =  "fathia_alma" 
 
  station = network.WLAN(network.STA_IF)
 
  if station.isconnected() == True:
      print("Already connected")
      return
 
  station.active(True)
  station.connect(ssid, password)
 
  while station.isconnected() == False:
      pass
 
  print("Connection successful")
  print(station.ifconfig())
connect()




import network
 
def connect():
  
  #ssid = "xxxx-xxxx"
  #password =  "yyyyyyyy"
  
  ssid = "Myxxxx"
  password =  "xxxx_xxxx" 
 
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




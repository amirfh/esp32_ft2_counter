


#import upip
#upip.install('picoweb')
#upip.install('micropython-logging')
#>>> upip.install('urtc')
#asyncio.sleep_ms(5)


import machine
import utime
import picoweb

import time
from micropython import const
from machine import Pin, Timer , SPI

import uasyncio as asyncio 

from machine import I2C  #, Pin ,  Timer
import urtc , time , sys

import ujson


mosi = Pin(23, Pin.OUT)
miso = Pin(19, mode = Pin.IN)
sck =  Pin(18, Pin.OUT)
cs = Pin(5 , Pin.OUT) 
spi = machine.SPI(baudrate = 100000, polarity=1, phase=0,sck = sck, mosi = mosi , miso = miso)

segment = { "blank": 0x80 , 
            "0": 0x3f , 
            "1" : 0x06 ,
            "2" : 0x5b ,
            "3" : 0x4f ,
            "4" : 0x66 ,
            "5" : 0x6d ,
            "6" : 0x7d ,
            "7" : 0x07 ,
            "8" : 0x7f ,
            "9" : 0x6f ,        
         }


BUTTON_A_PIN = const(4)
#BUTTON_B_PIN = const(33)

 
ip_address = None
actual = 0

app = picoweb.WebApp(__name__)

def AP_setup():
   global ip_address
   import network
   ap = network.WLAN(network.AP_IF)
   ap.active(True)
   ap.config(essid='ESP32-3')
   ap.config(authmode=3, password='123456789')
    #ip = 192.168.4.1 
   ip_address = "192.168.4.1"
   time.sleep(2)

def do_connect():
    import network
    global ip_address
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect("BOLT!-8D33", "385D63A5")
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
    ip_address = sta_if.ifconfig() [0]
 
def setup_pin():
   global led , rtc
   
   i2c = I2C(scl = Pin(22), sda = Pin(21))
   rtc = urtc.DS3231(i2c)

   led = Pin(2,Pin.OUT) 
   
   
class Button:
    """
    Debounced pin handler
    usage e.g.:
    def button_callback(pin):
        print("Button (%s) changed to: %r" % (pin, pin.value()))
    button_handler = Button(pin=Pin(32, mode=Pin.IN, pull=Pin.PULL_UP), callback=button_callback)
    """

    def __init__(self, pin, callback, trigger=Pin.IRQ_FALLING, min_ago=500):  #min_ago=300
        self.callback = callback
        self.min_ago = min_ago

        self._blocked = False
        self._next_call = time.ticks_ms() + self.min_ago

        pin.irq(trigger=trigger, handler=self.debounce_handler)

    def call_callback(self, pin):
        self.callback(pin)

    def debounce_handler(self, pin):
        if time.ticks_ms() > self._next_call:
            self._next_call = time.ticks_ms() + self.min_ago
            self.call_callback(pin)
        #else:
        #    print("debounce: %s" % (self._next_call - time.ticks_ms()))
        
        
def button_a_callback(pin):
   #print("Button A (%s) changed to: %r" % (pin, pin.value()))
   global actual , plan
   actual += 1
   seven_segment(actual , plan)
   save_config()
   print('actual= ' , actual ,'plan=',plan )


def button_b_callback(pin):
   print("Button B (%s) changed to: %r" % (pin, pin.value()))

 
def extIntHandler(pin):
   global actual , plan
   actual += 1
   print('actual= ' , actual ,'plan=',plan )

 
@app.route("/")
def send_index(req, resp):
   yield from app.sendfile(resp, 'index.html')
 
 
@app.route("/get_data_json")
def get_data_json(req, resp):
   global actual , plan , ct , run , running_sec
   t = rtc.datetime()   
   #add zero in front of number < 10
   t4 = checktime(str(t[4]))
   t5 = checktime(str(t[5]))
   t6 = checktime(str(t[6]))       
   #print(t4 , t5 , t6)
   now = t4 + ":" + t5 + ":" + t6      
   yield from picoweb.jsonify(resp, { 'actual': actual , 
                                      'plan' : plan , 
                                      'ct': ct ,
                                      'now': now ,
                                      'run': run ,
                                      'running_sec': running_sec })
 

@app.route("/set_data_plan")
def set_data_plan(req,resp):
    if req.method == "POST":
        yield from req.read_form_data()
    else:  # GET, apparently
        # Note: parse_qs() is not a coroutine, but a normal function.
        # But you can call it using yield from too.
        req.parse_qs()
        

@app.route("/query")
def query(req, resp):
    global plan , actual , ct
    queryString = req.qs 
    #print('queryString=',queryString)
    parameters = qs_parse(queryString)
    #print("Parameter 1 value: " + parameters["param1"])
    #print("Parameter 2 value: " + parameters["param2"])
    #print("Parameter 3 value: " + parameters["param3"])
    plan = int(parameters["param1"])
    actual = int(parameters["param2"])
    ct = int(parameters["param3"])
    seven_segment(actual , plan)
    print('from client<plan><actual><ct>:', plan , actual , ct )
    yield from picoweb.start_response(resp)
    
    '''
    yield from resp.awrite("Parameter 1 value: " + parameters["param1"] + "\n")
    yield from resp.awrite("Parameter 2 value: " + parameters["param2"])
    '''  
#### Parsing function
def qs_parse(qs):
 
   parameters = {}                 #  qs= "param1=23&param2=22&param3=3"
   ampersandSplit = qs.split("&")  # ['param1=23', 'param2=22', 'param3=3']
 
   for element in ampersandSplit:
     equalSplit = element.split("=")
     parameters[equalSplit[0]] = equalSplit[1]
   return parameters
 
def ct_loop():  #cycle time loop
   global plan , actual , run , ct , running_sec , led
   while True:
       led.value(not led.value())
       if run:  #with lock:
         running_sec += 1 
         if running_sec >= ct:
           plan += 1
           seven_segment(actual , plan)
           #save_config()
           print('plan=',plan)
           running_sec = 0
       yield int(1*1000)   #time.sleep(1)

        
         
def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

def checktime(ix):
    if (int(ix) < 10):
       ix = "0" + ix
    return ix 
   
def built_time_slot():
   global a,b,c,d,e,f,g,h,i,j,k,l
   global a1,b1,c1,d1,e1,f1,g1,h1,i1,j1,k1,l1
   global a2,b2,c2,d2,e2,f2,g2,h2,i2,j2,k2,l2
   global reset_shift1 , reset_shift2
   
   reset_shift1 = "07:59:00"
   
   reset_shift2 = "19:59:00"
   
   #SHIFT 1 SENIN - KAMIS
   a = "08:00:00"
   b = "10:00:00" 

   c = "10:10:00"
   d = "12:00:00"

   e = "13:00:00" 
   f = "14:30:00" 

   g = "14:40:00"
   h = "16:00:00" 

   i = "16:10:00"
   j = "18:00:00" 

   k = "18:10:00"
   l = "20:00:00"

   #SHIFT 1 JUMAT

   a1 = "08:00:00"
   b1 = "10:00:00"

   c1 = "10:10:00"
   d1 = "11:30:00"

   e1 = "12:45:00"
   f1 = "14:30:00"            

   g1 = "14:40:00"
   h1 = "16:00:00"

   i1 = "16:10:00"
   j1 = "18:00:00"

   k1 = "18:10:00"
   l1 = "20:00:00"            
   
   #SHIFT 2

   a2 = "20:00:00"
   b2 = "22:00:00"

   c2 = "22:10:00"
   d2 = "23:59:59"

   e2 = "00:00:30"
   f2 = "02:00:00"            

   g2 = "02:10:00"
   h2 = "03:30:00"

   i2 = "05:10:00"
   j2 = "07:10:00"

   k2 = "00:00:00"
   l2 = "00:00:00" 

   reset_shift1 = get_sec(reset_shift1)
   reset_shift2 = get_sec(reset_shift2)
 
   a = get_sec(a)
   b = get_sec(b)

   c = get_sec(c)
   d = get_sec(d)

   e = get_sec(e)
   f = get_sec(f)

   g = get_sec(g)
   h = get_sec(h)

   i = get_sec(i)
   j = get_sec(j)
 
   k = get_sec(k)
   l = get_sec(l)

   a1 = get_sec(a1)
   b1 = get_sec(b1)

   c1 = get_sec(c1)
   d1 = get_sec(d1)

   e1 = get_sec(e1)
   f1 = get_sec(f1)

   g1 = get_sec(g1)
   h1 = get_sec(h1)

   i1 = get_sec(i1)
   j1 = get_sec(j1)
 
   k1 = get_sec(k1)
   l1 = get_sec(l1)
   
   
   a2 = get_sec(a2)
   b2 = get_sec(b2)

   c2 = get_sec(c2)
   d2 = get_sec(d2)

   e2 = get_sec(e2)
   f2 = get_sec(f2)

   g2 = get_sec(g2)
   h2 = get_sec(h2)

   i2 = get_sec(i2)
   j2 = get_sec(j2)
 
   k2 = get_sec(k2)
   l2 = get_sec(l2)   
   
   
 
def run_check(): #time_slot check
   global  a,b,c,d,e,f,g,h,i,j , k,l
   global  a1,b1,c1,d1,e1,f1,g1,h1,i1,j1 , k1,l1
   global  a2,b2,c2,d2,e2,f2,g2,h2,i2,j2 , k2,l2
   global  led , rtc , run ,weekday , debug
   global  plan , actual , running_sec
   #led.value(button_actual.value())
  
   while True:
         #led.value(not led.value())
         
         print('run check')
         t = rtc.datetime()
         #weekday is 1-7 for Monday through Sunday.
         #Monday = 1
         #Tuesday	= 2
         #Wednesday	= 3
         #Thursday	= 4
         #Friday	= 5
         #Saturday = 6
         #Sunday = 7
                  
         weekday = int(t[3])
         #add zero in front of number < 10
         t4 = checktime(str(t[4]))
         t5 = checktime(str(t[5]))
         t6 = checktime(str(t[6]))
       
         #print(t4 , t5 , t6)
         now = t4 + ":" + t5 + ":" + t6
         print(now , 'weekday=',weekday)
         now = get_sec(now)
         
         #reset shift1
         if (now > reset_shift1) and (now < a):
           plan = 0
           actual = 0
           running_sec = 0
           
         #reset shift2
         if (now > reset_shift2) and (now < a2):
           plan = 0
           actual = 0
           running_sec = 0     
       
         if (now >= a) and (now < a2) and (weekday != 5): #SHIFT1 NON JUMAT

           if (a <= now) and (now <= b) :
             run = 1
             if debug:
                print('run=',run ,' slot a-b')
           
           elif  (c <= now) and (now <= d):  
             run = 1
             if debug:
               print('run=',run ,' slot c-d') 
           
           elif (e <= now) and (now <= f) :
             run = 1
             if debug:
               print('run=',run ,' slot e-f') 
           
           elif (g <= now) and (now <= h) :
             run = 1
             if debug:
               print('run=',run ,' slot g-h') 
             
           elif (i <= now) and (now <= j) :
             run = 1
             if debug:
               print('run=',run ,' slot i-j') 
               
           elif (k <= now) and (now <= l) :
             run = 1
             if debug:
               print('run=',run ,' slot k-l')             
               
           else:
             run = 0
             if debug:
               print('run=',run ,' shift1 non jumat')
         
         if (now >= a1) and (weekday == 5): #SHIFT1  JUMAT

           if (a1 <= now) and (now <= b1) :
             run = 1
             if debug:
               print('run=',run ,' slot a1-b1')
           
           elif  (c1 <= now) and (now <= d1):  
             run = 1
             if debug:
               print('run=',run ,' slot c1-d1') 
           
           elif (e1 <= now) and (now <= f1) :
             run = 1
             if debug:
               print('run=',run ,' slot e1-f1') 
           
           elif (g1 <= now) and (now <= h1) :
             run = 1
             if debug:
               print('run=',run ,' slot g1-h1') 
             
           elif (i1 <= now) and (now <= j1) :
             run = 1
             if debug:
               print('run=',run ,' slot i1-j1') 
               
           elif (k1 <= now) and (now <= l1) :
             run = 1
             if debug:
               print('run=',run ,' slot k1-l1')             
               
           else:
             run = 0
             if debug:
               print('run=',run ,' shift1 jumat' )
         
         if (now >= a2) :  #SHIFT2

           if (a2 <= now) and (now <= b2) :
             run = 1
             if debug:
                print('run=',run ,' slot a2-b2')
           
           elif  (c2 <= now) and (now <= d2):  
             run = 1
             if debug:
               print('run=',run ,' slot c2-d2') 
           
           elif (e2 <= now) and (now <= f2) :
             run = 1
             if debug:
               print('run=',run ,' slot e2-f2') 
           
           elif (g2 <= now) and (now <= h2) :
             run = 1
             if debug:
               print('run=',run ,' slot g2-h2') 
             
           elif (i2 <= now) and (now <= j2) :
             run = 1
             if debug:
               print('run=',run ,' slot i2-j2') 
               
           elif (k2 <= now) and (now <= l2) :
             run = 1
             if debug:
               print('run=',run ,' slot k2-l2')             
               
           else:
             run = 0
             if debug:
               print('run=',run ,' shift2')
  
             
         print('run=',run)
         yield int(10 * 1000)
          
    
CONFIG = {

    "plan": 0 ,
    "actual": 0 , 
    "ct": 5 ,
    
}

def load_config():
   import ujson as json
   global plan , actual , ct
   
   try:
     with open("/config.json") as f:
       config = json.loads(f.read())
   except (OSError, ValueError):
       print("Couldn't load /config.json")
       save_config()
   else:
       CONFIG.update(config)
       print("Loaded config from /config.json")
       #assign to var
       #sensor_pin = machine.ADC(CONFIG['sensor_pin'])
       plan = config['plan']
       actual = config['actual']
       ct = config['ct'] 
       seven_segment(actual , plan)
       print('plan=', plan , actual , ct)
       print(config)

def save_config():
   import ujson as json
   global plan , actual , ct
   
   config = {

     "plan": plan ,
     "actual": actual , 
     "ct": ct ,
    
     }
   
   CONFIG.update(config)
   
   try:
     with open("/config.json", "w") as f:
       f.write(json.dumps(CONFIG))
   except OSError:
       print("Couldn't save /config.json")    
 
def write_config():
   global plan , actual , cycle_time
   config = {'plan': plan, 'actual': actual , 'ct': ct}
   f = open('config.json', 'w')
   f.write(ujson.dumps(config))
   f.close() 
 
def read_config(): 
   global plan , actual , ct
   f = open('config.json', 'r')
   config_read = ujson.loads(f.read())
   #assign to var
   #sensor_pin = machine.ADC(CONFIG['sensor_pin'])
   plan = config_read['plan']
   actual = config_read['actual']
   ct = config_read['ct'] 
   print(config_read)
   
def seven_segment(val1,val2):
      mystring = str(val1)
      if len(mystring) == 1 :
         b1 = segment[mystring[0]]
         b2 = 0
         b3 = 0
         b4 = 0
         
      if len(mystring) == 2 :   
         b1 = segment[mystring[1]]
         b2 = segment[mystring[0]]
         b3 = 0
         b4 = 0
      if len(mystring) == 3:
         b1 = segment[mystring[2]]
         b2 = segment[mystring[1]]
         b3 = segment[mystring[0]]
         b4 = 0
      if len(mystring) == 4:
         b1 = segment[mystring[3]]
         b2 = segment[mystring[2]]
         b3 = segment[mystring[1]]               
         b4 = segment[mystring[0]]
 
      mystring = str(val2)
      if len(mystring) == 1 :
         b5 = segment[mystring[0]]
         b6 = 0
         b7 = 0
         b8 = 0
         
      if len(mystring) == 2 :   
         b5 = segment[mystring[1]]
         b6 = segment[mystring[0]]
         b7 = 0
         b8 = 0
      if len(mystring) == 3:
         b5 = segment[mystring[2]]
         b6 = segment[mystring[1]]
         b7 = segment[mystring[0]]
         b8 = 0
      if len(mystring) == 4:
         b5 = segment[mystring[3]]
         b6 = segment[mystring[2]]
         b7 = segment[mystring[1]]               
         b8 = segment[mystring[0]]

      cs.value(0)
      #spi.write(bytes([b8 , b7 , b6 , b5 ,  b4 , b3 , b2 , b1])) # send 4 bytes on the bus
      spi.write(bytes([b1 , b2 , b3 , b4 ,  b5 , b6 , b7 , b8])) # send 4 bytes on the bus
      cs.value(1)
 

if __name__ == '__main__': 
   
   #do_connect() #STATION MODE
   
   AP_setup()  #AP MODE 192.168.4.1
   
   #p4 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)
   #p4.irq(trigger=machine.Pin.IRQ_FALLING, handler=extIntHandler)
   
   setup_pin()
   
   led.value(0)
   actual = 0
   plan = 0
   running_sec = 0
   ct = 5  #sec
   run = True
   debug = True #False
       
   load_config()
       
   built_time_slot()
          
   button_a = Button(pin=Pin(BUTTON_A_PIN, mode=Pin.IN, pull=Pin.PULL_UP), callback=button_a_callback)
   #button_b = Button(pin=Pin(BUTTON_B_PIN, mode=Pin.IN, pull=Pin.PULL_UP), callback=button_b_callback)
  
   loop = asyncio.get_event_loop()
   loop.create_task(ct_loop())
   loop.create_task(run_check())
   
   app.run(debug=1, host=ip_address, port=80)






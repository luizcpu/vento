import esp32, network, json, ssd1306, utils, math, onewire, ds2423, ads1x15
from machine import Pin, SoftI2C, ADC, Timer
from micropyserver import MicroPyServer
from time import sleep

ONE_WIRE_PIN = 14

data_check_timer = Timer(2)

i2c = SoftI2C(scl=Pin(32), sda=Pin(33), freq=400000) # IO33=485_EN / IO32=CFG
display = ssd1306.SSD1306_I2C(128, 64, i2c)
adc = ads1x15.ADS1115(i2c, address = 72, gain = 2)

ow = onewire.OneWire(Pin(ONE_WIRE_PIN))
counter = ds2423.DS2423(ow)

for rom in counter.scan():
    counter.begin(bytearray(rom))

lan = network.LAN(mdc=Pin(23), mdio=Pin(18),
                  phy_type=network.PHY_LAN8720, phy_addr=1,
                  power=Pin(16))

if not lan.active():
    lan.active(True)

while not lan.isconnected():
    pass

sleep(1)
ip_ok = False
maxt = 0
while not ip_ok:
    endip = lan.ifconfig()[0]
    if endip != "0.0.0.0":
        ip_ok = True
    maxt += 1
    if maxt >= 10:
        break
    sleep(1)

display.fill(0)
display.text('IP:', 0, 0, 1)
display.text(endip, 32, 0, 1)
display.show()

raio_anemometro = 160 # Total diâmetro até no centro do caneco 160mm, não na extemidade que seria de 210mm.
amostragem = 5
contador = counter.get_count("DS2423_COUNTER_A")
rpm = 0

def calcula(timer):
    global contador
    global raio_anemometro
    global dir_nome
    global dir_grau
    global velocidade
    global amostragem
    global rpm
    contador_anterior = contador
    contador = counter.get_count("DS2423_COUNTER_A")
    if contador < contador_anterior: # trata a virada do contador DS2423 de 32 bits
        voltas = (4294967295 - contador_anterior + contador)
    else:
        voltas = contador - contador_anterior
    val_adc = adc.read()
    
    if val_adc <= 1142: 
        dir_grau = 135
        dir_nome = "Sudeste"
    elif val_adc <= 2696:
        dir_grau = 90
        dir_nome = "Leste"
    elif val_adc <= 3513:  
        dir_grau = 45
        dir_nome = "Nordeste"
    elif val_adc <= 4437:
        dir_grau = 0
        dir_nome = "Norte"
    elif val_adc <= 5740:
        dir_grau = 315
        dir_nome = "Noroeste"
    elif val_adc <= 7926:
        dir_grau = 270
        dir_nome = "Oeste"
    elif val_adc <= 12676:
        dir_grau = 225
        dir_nome = "Sudoeste"
    else:
        dir_grau = 180
        dir_nome = "Sul"

    rpm = voltas*(60/amostragem)
    velocidade = round((((4 * math.pi * raio_anemometro * rpm)/60)/1000)*3.6,1)
    print('Valor ADC:', val_adc, 'Contador:', contador, 'Voltas:', contador - contador_anterior, 'direção:', dir_nome, 'RPM:', rpm, 'Velocidade:', velocidade)
    winddir = "Direcao: " + str(dir_nome)
    display.fill(0)
    display.text('IP:', 0, 0, 1)
    display.text(endip, 32, 0, 1)
    display.text('KM/h:' + str(velocidade), 0, 16, 1)
    display.text('RPM:' + str(rpm), 0, 32, 1)
    display.text('Dir.:' + dir_nome, 0, 48, 1)   
    display.show()

def winddir_speed(request):
    ''' rota principal '''
    global velocidade
    global dir_nome
    global dir_grau
    global rpm
    json_str = json.dumps({"speed": velocidade, "winddir": dir_nome, "wingrau": dir_grau, "rpm": rpm})
    server.send("HTTP/1.0 200 OK\n")
    server.send("Content-Type: application/json\n")
    server.send("Connection: close\n\n")      
    server.send(json_str)

data_check_timer.init(period=amostragem*1000, mode=Timer.PERIODIC, callback=calcula)

server = MicroPyServer()
server.add_route("/", winddir_speed)
server.start()


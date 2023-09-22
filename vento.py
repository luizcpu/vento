import esp32, network, json, ssd1306, utils, math
from machine import Pin, SoftI2C, ADC, Timer
from micropyserver import MicroPyServer
from time import sleep, ticks_ms, ticks_diff

WIND_DIR_PIN = 4
WIND_SPD_PIN = 35

wind_dir_pin = ADC(Pin(WIND_DIR_PIN))
wind_speed_pin = Pin(WIND_SPD_PIN, Pin.IN)

data_check_timer = Timer(2)

i2c = SoftI2C(scl=Pin(32), sda=Pin(33), freq=400000) # IO33=485_EN / IO32=CFG

display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Visto no site do MicroPython - Wireless-Tag's WT32-ETH01 v1.4
lan = network.LAN(mdc=Pin(23), mdio=Pin(18),
                  phy_type=network.PHY_LAN8720, phy_addr=1,
                  power=Pin(16))

if not lan.active():
    lan.active(True)

while not lan.isconnected():
    pass

wind_speed_last_int = ticks_ms()
contador = 0
raio_anemometro = 147

sleep(3)
endip = lan.ifconfig()[0]
display.fill(0)
display.text('IP:', 0, 0, 1)
display.text(endip, 32, 0, 1)
display.show()


def calcula(timer):
    global contador
    global raio_anemometro
    global direcao
    global velocidade
    rpm = contador
    contador = 0
    val_adc = wind_dir_pin.read_u16() # Faixa 0-65535
    if val_adc <= 0.27:
        dir_grau = 315
        dir_nome = "Noroeste"
    elif val_adc <= 0.32:
        dir_grau = 270
        dir_nome = "Oeste"
    elif val_adc <= 0.38:
        dir_grau = 225
        dir_nome = "Sudoeste"
    elif val_adc <= 0.45:
        dir_grau = 180
        dir_nome = "Sul"
    elif val_adc <= 0.57: 
        dir_grau = 135
        dir_nome = "Sudeste"
    elif val_adc <= 0.75:
        dir_grau = 90
        dir_nome = "Leste"
    elif val_adc <= 1.25:  
        dir_grau = 45
        dir_nome = "Nordeste"
    else:
        dir_grau = 0
        dir_nome = "Norte"
    velocidade = round((((4 * math.pi * raio_anemometro * rpm)/5)/1000)*3.6,1)
    print('calcula: ', val_adc, 'direção:', dir_nome, 'RPM:', rpm, 'Velocidade:', velocidade)
    winddir = "Direcao: " + str(dir_nome)
    display.fill(0)
    display.text('IP:', 0, 0, 1)
    display.text(endip, 32, 0, 1)
    display.text('KM/h:' + str(velocidade), 0, 16, 1)
    display.text('RPM:' + str(rpm), 0, 32, 1)
    display.text('Dir.:' + dir_nome, 0, 48, 1)   
    display.show()

def wind_speed_int(irq):
    global wind_speed_last_int
    global contador
    print('vento', contador)
    if ticks_diff(ticks_ms(), wind_speed_last_int) > 5:  # Não menos que 5ms entre pulsos, tratamento de debounce
        wind_speed_last_int = ticks_ms()
        contador += 1

def winddir_speed(request):
    ''' rota principal '''
    global velocidade
    global direcao
    json_str = json.dumps({"speed": velocidade, "winddir": direcao})
    server.send("HTTP/1.0 200 OK\n")
    server.send("Content-Type: application/json\n")
    server.send("Connection: close\n\n")      
    server.send(json_str)


wind_speed_pin.irq(trigger=Pin.IRQ_RISING, handler=wind_speed_int) # executa rotina "wind_speed_int" toda vez que o pino de entrar entrar em nível alto

data_check_timer.init(period=5000, mode=Timer.PERIODIC, callback=calcula) # executa rotina "calcula" de 5 em 5 segundos

server = MicroPyServer()
server.add_route("/", winddir_speed)
server.start()

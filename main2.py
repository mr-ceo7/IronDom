import os
import socket
import network
from machine import Pin, PWM, time_pulse_us
from utime import sleep_us, sleep_ms

# Hardware mapping
TRIG_PIN = 7
ECHO_PIN = 6  # Update if your echo pin is different from GP6
SERVO_X_PIN = 1
SERVO_Y_PIN = 0
IR_LEFT_PIN = 3
IR_RIGHT_PIN = 4
IR_BOTTOM_PIN = 2
IR_TOP_PIN = 5
RED_LED_PIN = 22
WHITE_LED_PIN = 21
BLUE_LED_PIN = 9


# Wi-Fi settings
USE_AP_MODE = False
AP_SSID = 'PicoRadar'
AP_PASSWORD = 'radar1234'
STA_SSID = 'dev'
STA_PASSWORD = '12345678'

DEFAULT_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta http-equiv='refresh' content='2'>
  <title>Pico Radar Dashboard</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #070916; color: #eef2ff; }
    .wrapper { max-width: 980px; margin: 0 auto; padding: 20px; }
    .header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
    .title { margin: 0; font-size: 2rem; }
    .subtitle { color: #9fb1ff; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 18px; }
    .card { border-radius: 18px; background: rgba(18, 25, 50, 0.95); border: 1px solid rgba(120, 156, 255, 0.16); padding: 18px; box-shadow: 0 14px 50px rgba(0,0,0,0.18); }
    .card h2 { margin-top: 0; margin-bottom: 14px; font-size: 1.1rem; color: #d4deff; }
    .row { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; }
    .label { color: #98b4ff; }
    .value { font-size: 1.05rem; font-weight: 700; }
    .radar { position: relative; padding-top: 100%; background: radial-gradient(circle at center, rgba(95, 166, 255, 0.18), transparent 60%); border-radius: 50%; border: 1px solid rgba(255,255,255,0.08); overflow: hidden; }
    .radar::before, .radar::after { content: ''; position: absolute; inset: 0; border-radius: 50%; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06); }
    .radar-line-x, .radar-line-y { position: absolute; background: rgba(255,255,255,0.08); }
    .radar-line-x { left: 50%; top: 0; bottom: 0; width: 1px; transform: translateX(-50%); }
    .radar-line-y { top: 50%; left: 0; right: 0; height: 1px; transform: translateY(-50%); }
    .radar-dot { position: absolute; width: 14px; height: 14px; border-radius: 50%; background: #ff5f7d; box-shadow: 0 0 18px rgba(255,95,125,0.5); transform: translate(-50%, -50%); }
    .meter { height: 14px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; }
    .meter-bar { height: 100%; width: {{DISTANCE_PERCENT}}%; background: linear-gradient(90deg, #5dd8ff, #7c7cff); transition: width 0.25s ease; }
    .chip { display: inline-flex; justify-content: space-between; width: 100%; padding: 10px 12px; border-radius: 14px; background: rgba(255,255,255,0.05); color: #e8eeff; margin-bottom: 10px; }
    .pill { display: inline-flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px; font-weight: 700; }
    .pill-green { background: rgba(84, 255, 176, 0.12); color: #bdfdd3; }
    .pill-blue { background: rgba(137, 195, 255, 0.14); color: #cfe6ff; }
    .pill-red { background: rgba(255, 96, 96, 0.18); color: #ffb8b8; }
  </style>
</head>
<body>
  <div class='wrapper'>
    <div class='header'>
      <div>
        <h1 class='title'>Pico Radar Dashboard</h1>
        <p class='subtitle'>IP: <strong>{{IP}}</strong> · Lock: <strong>{{LOCK}}</strong></p>
      </div>
      <div class='pill {{STATUS_CLASS}}'>{{STATUS_TEXT}}</div>
    </div>

    <div class='grid'>
      <div class='card'>
        <h2>Radar view</h2>
        <div class='radar'>
          <div class='radar-line-x'></div>
          <div class='radar-line-y'></div>
          <div class='radar-dot' style='left:{{DOT_X}}%; top:{{DOT_Y}}%;'></div>
        </div>
        <div class='row'><span class='label'>Servo X</span><span class='value'>{{X_ANGLE}}°</span></div>
        <div class='row'><span class='label'>Servo Y</span><span class='value'>{{Y_ANGLE}}°</span></div>
      </div>
      <div class='card'>
        <h2>Object status</h2>
        <div class='row'><span class='label'>Distance</span><span class='value'>{{DISTANCE}}</span></div>
        <div class='meter'><div class='meter-bar'></div></div>
        <div class='chip'><span>IR left</span><strong>{{LEFT_IR}}</strong></div>
        <div class='chip'><span>IR right</span><strong>{{RIGHT_IR}}</strong></div>
        <div class='chip'><span>IR top</span><strong>{{TOP_IR}}</strong></div>
        <div class='chip'><span>IR bottom</span><strong>{{BOTTOM_IR}}</strong></div>
      </div>
      <div class='card'>
        <h2>LEDs</h2>
        <div class='chip'><span>Red</span><strong>{{RED_LED}}</strong></div>
        <div class='chip'><span>White</span><strong>{{WHITE_LED}}</strong></div>
        <div class='chip'><span>Blue</span><strong>{{BLUE_LED}}</strong></div>
      </div>
    </div>
  </div>
</body>
</html>"""

# Servo constants
SERVO_FREQ = 50
SERVO_MIN_US = 500
SERVO_MAX_US = 2500
SERVO_PERIOD_US = 20_000

RIGHT=76
LEFT=71
CENTER=75
UP=90
DOWN=86
CENTER_Y=89



# Radar/tracking constants
IR_ACTIVE_LOW = True
CLOSE_DISTANCE_CM = 40
TRACKING_STEP = 1
SCAN_STEP = 1
SCAN_MIN_ANGLE = 20
SCAN_MAX_ANGLE = 160

def wifi_connect():
    wlan = None
    if not USE_AP_MODE and STA_SSID:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(STA_SSID, STA_PASSWORD)
        print('Connecting to Wi-Fi...')
        for _ in range(20):
            if wlan.isconnected():
                break
            sleep_ms(500)
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print('Connected to Wi-Fi:', ip)
            return ip
        print('Station mode failed, fallback to AP mode')
        wlan.active(False)

    wlan = network.WLAN(network.AP_IF)
    wlan.active(True)
    if AP_PASSWORD:
        wlan.config(essid=AP_SSID, password=AP_PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
    else:
        wlan.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    ip = wlan.ifconfig()[0]
    print('AP mode active on', ip)
    return ip



def angle_to_duty(angle):
    """Convert 0-180 degrees into a 16-bit PWM duty value."""
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    pulse_us = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle // 180
    duty_u16 = int(pulse_us * 65535 // SERVO_PERIOD_US)
    return duty_u16


class Servo:
    def __init__(self, pin_num):
        self.pwm = PWM(Pin(pin_num))
        self.pwm.freq(SERVO_FREQ)
        self.angle = 90
        self.move(self.angle)

    def move(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.duty_u16(angle_to_duty(self.angle))

    def move_toward(self, target_angle, step=1):
        target_angle = max(0, min(180, target_angle))
        if self.angle < target_angle:
            self.move(self.angle + step)
        elif self.angle > target_angle:
            self.move(self.angle - step)

    def deinit(self):
        self.pwm.deinit()


class Ultrasonic:
    def __init__(self, trig_pin, echo_pin):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.trig.off()
        sleep_ms(50)

    def distance_cm(self, timeout_us=30000):
        self.trig.off()
        sleep_us(2)
        self.trig.on()
        sleep_us(10)
        self.trig.off()

        try:
            pulse_time = time_pulse_us(self.echo, 1, timeout_us)
        except OSError:
            return None

        if pulse_time < 0:
            return None

        # speed of sound 343 m/s = 0.0343 cm/us, divide by 2 for round trip
        return pulse_time * 0.0343 / 2


class IRArray:
    def __init__(self, left_pin, right_pin, top_pin, bottom_pin):
        self.left = Pin(left_pin, Pin.IN, Pin.PULL_UP)
        self.right = Pin(right_pin, Pin.IN, Pin.PULL_UP)
        self.top = Pin(top_pin, Pin.IN, Pin.PULL_UP)
        self.bottom = Pin(bottom_pin, Pin.IN, Pin.PULL_UP)

    def _active(self, raw_value):
        return raw_value == 0 if IR_ACTIVE_LOW else raw_value == 1

    def read(self):
        raw = {
            'left': self.left.value(),
            'right': self.right.value(),
            'top': self.top.value(),
            'bottom': self.bottom.value(),
        }
        return {k: self._active(v) for k, v in raw.items()}

    def any_active(self):
        values = self.read()
        return any(values.values()), values


class StatusLEDs:
    def __init__(self, red_pin, white_pin, blue_pin):
        self.red = Pin(red_pin, Pin.OUT)
        self.white = Pin(white_pin, Pin.OUT)
        self.blue = Pin(blue_pin, Pin.OUT)

    def all_off(self):
        self.red.off()
        self.white.off()
        self.blue.off()

    def set(self, red=False, white=False, blue=False):
        self.red.value(1 if red else 0)
        self.white.value(1 if white else 0)
        self.blue.value(1 if blue else 0)


class DashboardServer:
    def __init__(self, ip):
        self.ip = ip
        self.server_socket = None
        self.template = self._load_template()
        self.state = {
            'distance': None,
            'tracking': False,
            'lock_status': 'searching',
            'servo_x_angle': CENTER,
            'servo_y_angle': CENTER_Y,
            'ir_states': {'left': False, 'right': False, 'top': False, 'bottom': False},
            'red_led': False,
            'white_led': False,
            'blue_led': False,
        }

    def _load_template(self):
        search_paths = ['dashboard_template.html', './dashboard_template.html', '/dashboard_template.html']
        try:
            search_paths.append(os.getcwd() + '/dashboard_template.html')
        except OSError:
            pass

        for path in search_paths:
            try:
                with open(path, 'r') as f:
                    print('Loaded dashboard template from', path)
                    return f.read()
            except OSError:
                continue

        print('Dashboard template not found, using fallback template')
        return DEFAULT_DASHBOARD_TEMPLATE

    def _render_template(self, values):
        html = self.template
        for key, val in values.items():
            html = html.replace('{{%s}}' % key, str(val))
        return html

    def update_state(self, distance, tracking, lock_status, servo_x_angle, servo_y_angle,
                     ir_states, red_led, white_led, blue_led):
        self.state['distance'] = distance
        self.state['tracking'] = tracking
        self.state['lock_status'] = lock_status
        self.state['servo_x_angle'] = servo_x_angle
        self.state['servo_y_angle'] = servo_y_angle
        self.state['ir_states'] = ir_states
        self.state['red_led'] = red_led
        self.state['white_led'] = white_led
        self.state['blue_led'] = blue_led

    def status_html(self):
        distance = self.state['distance']
        distance_text = 'timeout' if distance is None else '{:.1f} cm'.format(distance)
        distance_percent = 0 if distance is None else min(100, int(distance / 200 * 100))
        tracking = self.state['tracking']
        values = {
            'IP': self.ip,
            'STATUS_CLASS': 'pill-green' if tracking else 'pill-blue',
            'STATUS_TEXT': 'Tracking' if tracking else 'Searching',
            'DISTANCE': distance_text,
            'LOCK': self.state['lock_status'],
            'X_ANGLE': self.state['servo_x_angle'],
            'Y_ANGLE': self.state['servo_y_angle'],
            'LEFT_IR': 'ON' if self.state['ir_states']['left'] else 'OFF',
            'RIGHT_IR': 'ON' if self.state['ir_states']['right'] else 'OFF',
            'TOP_IR': 'ON' if self.state['ir_states']['top'] else 'OFF',
            'BOTTOM_IR': 'ON' if self.state['ir_states']['bottom'] else 'OFF',
            'RED_LED': 'ON' if self.state['red_led'] else 'OFF',
            'WHITE_LED': 'ON' if self.state['white_led'] else 'OFF',
            'BLUE_LED': 'ON' if self.state['blue_led'] else 'OFF',
            'DOT_X': min(100, max(0, int(self.state['servo_x_angle'] / 180 * 100))),
            'DOT_Y': min(100, max(0, int(self.state['servo_y_angle'] / 180 * 100))),
            'DISTANCE_PERCENT': distance_percent,
        }
        return self._render_template(values)

    def start(self):
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        self.server_socket = socket.socket()
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(addr)
        self.server_socket.listen(1)
        self.server_socket.settimeout(0.2)
        print('Dashboard server running on http://%s/' % self.ip)

    def handle_clients(self):
        if self.server_socket is None:
            return
        try:
            conn, addr = self.server_socket.accept()
        except OSError:
            return

        try:
            conn.recv(1024)
            conn.send('HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n')
            conn.send(self.status_html())
        except OSError:
            pass
        finally:
            conn.close()

    def stop(self):
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None


def main():
    ip = wifi_connect()
    ultrasonic = Ultrasonic(TRIG_PIN, ECHO_PIN)
    ir = IRArray(IR_LEFT_PIN, IR_RIGHT_PIN, IR_TOP_PIN, IR_BOTTOM_PIN)
    servo_x = Servo(SERVO_X_PIN)
    servo_y = Servo(SERVO_Y_PIN)
    leds = StatusLEDs(RED_LED_PIN, WHITE_LED_PIN, BLUE_LED_PIN)
    dashboard = DashboardServer(ip)
    dashboard.start()

    print('Started robot controller')
    led_flash = False
    scan_dir_x = 1
    servo_x.move(CENTER)
    servo_y.move(CENTER_Y)
    try:
        while True:
            dist = ultrasonic.distance_cm()
            tracking, ir_states = ir.any_active()
            print('IR states:', ir_states)

            red_state = True
            blue_state = True
            white_state = True

            if tracking:
                # use the IR sensors to slowly center the object
                if ir_states['left']:
                    servo_x.move(RIGHT)
                elif ir_states['right']:
                    servo_x.move(LEFT)
                else:
                    servo_x.move_toward(CENTER)

                if ir_states['top']:
                    servo_y.move(UP)
                elif ir_states['bottom']:
                    servo_y.move(DOWN)
                else:
                    servo_y.move_toward(CENTER_Y)

                white_state = led_flash
                if dist is not None:
                    if dist <= CLOSE_DISTANCE_CM:
                        red_state = led_flash
                    else:
                        blue_state = led_flash

            else:
                servo_x.move(CENTER)
                servo_y.move(CENTER_Y)
                # no object locked: scan slowly like a radar sweep
                # servo_x.move(servo_x.angle + scan_dir_x * SCAN_STEP)
                # if servo_x.angle <= SCAN_MIN_ANGLE or servo_x.angle >= SCAN_MAX_ANGLE:
                scan_dir_x *= -1
                # servo_y.move(90)

            leds.set(red=red_state, white=white_state, blue=blue_state)
            dashboard.update_state(
                dist,
                tracking,
                'tracking' if tracking else 'searching',
                servo_x.angle,
                servo_y.angle,
                ir_states,
                red_state,
                white_state,
                blue_state,
            )
            dashboard.handle_clients()

            if dist is None:
                print('Distance: timeout')
            else:
                print('Distance: {:.1f} cm'.format(dist))

            led_flash = not led_flash
            sleep_ms(250)
    except KeyboardInterrupt:
        pass
    finally:
        dashboard.stop()
        leds.all_off()
        servo_x.deinit()
        servo_y.deinit()
        print('Stopped robot controller')


if __name__ == '__main__':
    main()

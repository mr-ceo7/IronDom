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

# Servo constants
SERVO_FREQ = 50
SERVO_MIN_US = 500
SERVO_MAX_US = 2500
SERVO_PERIOD_US = 20_000

RIGHT=76
LEFT=71
CENTER=75
UP=93
DOWN=84
CENTER_Y=89


# Radar/tracking constants
IR_ACTIVE_LOW = True
CLOSE_DISTANCE_CM = 40
TRACKING_STEP = 1
SCAN_STEP = 1
SCAN_MIN_ANGLE = 20
SCAN_MAX_ANGLE = 160


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


def main():
    ultrasonic = Ultrasonic(TRIG_PIN, ECHO_PIN)
    ir = IRArray(IR_LEFT_PIN, IR_RIGHT_PIN, IR_TOP_PIN, IR_BOTTOM_PIN)
    servo_x = Servo(SERVO_X_PIN)
    servo_y = Servo(SERVO_Y_PIN)
    leds = StatusLEDs(RED_LED_PIN, WHITE_LED_PIN, BLUE_LED_PIN)

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

            red_state = False
            blue_state = False
            white_state = False

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
                # no object locked: scan slowly like a radar sweep
                # servo_x.move(servo_x.angle + scan_dir_x * SCAN_STEP)
                # if servo_x.angle <= SCAN_MIN_ANGLE or servo_x.angle >= SCAN_MAX_ANGLE:
                    scan_dir_x *= -1
                # servo_y.move(90)

            leds.set(red=red_state, white=white_state, blue=blue_state)

            if dist is None:
                print('Distance: timeout')
            else:
                print('Distance: {:.1f} cm'.format(dist))

            led_flash = not led_flash
            sleep_ms(250)
    except KeyboardInterrupt:
        pass
    finally:
        leds.all_off()
        servo_x.deinit()
        servo_y.deinit()
        print('Stopped robot controller')


if __name__ == '__main__':
    main()

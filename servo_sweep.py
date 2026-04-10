from machine import Pin, PWM
from utime import sleep_ms

# Change this pin if needed
SERVO_PIN = 1
SERVO_FREQ = 50
SERVO_MIN_US = 500
SERVO_MAX_US = 2500
SERVO_PERIOD_US = 20000
SWEEP_STEP = 1
SWEEP_DELAY_MS = 200


def angle_to_duty(angle):
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    pulse_us = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle // 180
    return int(pulse_us * 65535 // SERVO_PERIOD_US)


class Servo:
    def __init__(self, pin_num):
        self.pwm = PWM(Pin(pin_num))
        self.pwm.freq(SERVO_FREQ)
        self.angle = 0
        self.move(self.angle)

    def move(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.duty_u16(angle_to_duty(self.angle))
        print('Servo angle:', self.angle)

    def deinit(self):
        self.pwm.deinit()


def main():
    servo = Servo(SERVO_PIN)
    print('Starting sweep from 0 to 180...')
    try:
        for angle in range(71, 76, SWEEP_STEP):
            servo.move(angle)
            sleep_ms(1000)
        print('Sweep complete. Servo stopped at 180.')
    except KeyboardInterrupt:
        print('Sweep interrupted at angle', servo.angle)
    finally:
        servo.deinit()


if __name__ == '__main__':
    main()

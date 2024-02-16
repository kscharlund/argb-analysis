from pprint import pprint
import sys


MIN_RST_T = 0.000006


class WS2812BParser:
    def __init__(self):
        self.timestamps = []
        self.bits = []
        sys.stdin.readline()
        for line in sys.stdin:
            ts_s, bit_s = line.split(',')
            self.timestamps.append(float(ts_s))
            self.bits.append(int(bit_s))
        self.index = 0
        self.start_times = []

    def ts(self, offset=0):
        return self.timestamps[self.index + offset]

    def bit(self, offset=0):
        return self.bits[self.index + offset]

    def next(self, offset=1):
        self.index += offset

    def resync(self):
        if self.bit():
            self.next()
        while True:
            lo_time = self.ts(1) - self.ts()
            if lo_time > MIN_RST_T:
                self.next()
                print(f'Resynced, current ts is {self.ts()} ({self.index})')
                return
            print(f'{lo_time=}')
            self.next(2)

    def next_bit(self):
        if not self.bit():
            assert self.index == len(self.bits) - 1
            raise StopIteration
        ts_rise = self.ts()
        self.next()
        ts_fall = self.ts()
        t_hi = ts_fall - ts_rise
        val = int(t_hi > 0.0000005)
        self.next()
        t_lo = self.ts() - ts_fall
        reset = t_lo > MIN_RST_T
        return val, reset

    def next_triplet(self):
        res = []
        reset = False
        for channel in range(3):
            assert not reset
            val = 0
            for bit_i in range(8):
                assert not reset
                val <<= 1
                bit, reset = self.next_bit()
                val |= bit
            res.append(val)
        return (res[1], res[0], res[2]), reset

    def rgb_triplets(self):
        try:
            self.resync()
            while True:
                triplets = []
                self.start_times.append(self.ts())
                while True:
                    triplet, reset = self.next_triplet()
                    if triplet:
                        triplets.append(triplet)
                    if reset:
                        break
                yield triplets
        except StopIteration:
            pass


parser = WS2812BParser()
updates = list(parser.rgb_triplets())
print(len(updates))
cycle_len = 0
commands = {}
for j, triplets in enumerate(updates):
    # The ARGB controller sends 6 LED triplets repeated 10 times.
    for i in range(6, len(triplets), 6):
        assert triplets[i:i+6] == triplets[i-6:i]
    # The animation cycles after 955 unique color combinations.
    combo = tuple(triplets[:6])
    if not cycle_len:
        if combo in commands:
            print(f'Cycle at {j}, previously {commands[combo]}')
            cycle_len = j - commands[combo]
        else:
            commands[combo] = j
    else:
        assert commands[combo] == j % cycle_len, f"{j} {commands[combo]}"

for command in commands:
    print(" ".join(f"#{r:02X}{g:02X}{b:02X}" for r, g, b in command))
    #print(",".join(f"{r},{g},{b}" for r, g, b in command))

leds = []
for i in range(6):
    leds.append([triplets[i] for triplets in commands])

print()
for i, led_seq in enumerate(leds):
    print(i)
    print(f'Average R: {sum(t[0] for t in led_seq)/len(led_seq)}')
    print(f'Average G: {sum(t[1] for t in led_seq)/len(led_seq)}')
    print(f'Average B: {sum(t[2] for t in led_seq)/len(led_seq)}')
    break

print()
offsets = [0]
for i in range(1, 6):
    base = leds[0]
    comp = leds[i]
    for offset in range(len(base)):
        comp.append(comp.pop(0))
        if base == comp:
            print(f'Cycle found at offset {offset} for LED {i}')
            offsets.append(offset)
            break
    else:
        print(f'No cycle found for LED {i}')
print([o1 - o0 for o0, o1 in zip(offsets, offsets[1:] + [955])])

print()
color_lengths = [t1 - t0 for t0, t1 in zip(parser.start_times[:-1], parser.start_times[1:])]
color_lengths = color_lengths[:-1]
print(f'Color lenghts: min {min(color_lengths):.5f} s, max {max(color_lengths):.5f} s, mean {sum(color_lengths)/len(color_lengths):.5f} s')

import sys


class Rover:
	def __init__(self):
		self.cruse_h_speed_max = 80
		self.landing_h_speed_max = 20
		self.landing_v_speed_max = 40

		self.hits = list()
		self.scan_terrain() # Load the surface into memory
		# logs = str(safe_x_min)+", "+str(safe_x_max)+", "+str(safe_y)
		self.safe_y = 0
		self.like_y_hits = 0
		self.safe_x_min = 6999
		self.safe_x_max = 0
		self.zone_size = self.safe_x_max - self.safe_x_min
		self.x_center = 3500
		self.center = [self.x_center, self.safe_y]
		last = [7000, -1]
		for cord in self.hits:
			if cord[1] == last[1]:
				self.safe_x_max = cord[0]
				self.safe_x_min = last[0]
				self.safe_y = cord[1]
				break
			else:
				last = cord

		self.x_center = self.safe_x_min + ((self.safe_x_max - self.safe_x_min) / 2)
		self.loop = 0
		self.wait = 0
		self.correcting_speed = False
		self.correction_angle = 0
		self.total_fuel = 0
		self.total_distance = 0
		self.remaining_dist_x = 0
		self.normalized_dist = 0
		self.x_diff = 0
		#
		# Ship telemetry
		#
		self.x = 0
		self.y = 0
		self.h_speed = 0
		self.abs_h_speed = 0
		self.v_speed = 0
		self.abs_v_speed = 0
		self.fuel = 0
		self.normalized_fuel = 0
		self.rotate = 0
		self.power = 0
		self.alt = 0
		self.normalized_alt = 0
		# # #
		self.run()  # game loop
		# # #

	def run(self):
		while True:
			x, y, h_speed, v_speed, fuel, rotate, power = [int(i) for i in input().split()]
			# Update telemetry
			self.update_telemetry(x, y, h_speed, v_speed, fuel, rotate, power)

			power_offset = 0
			set_power = self.power
			angle = self.rotate
			in_zone = self.in_zone(self.x)
			if not in_zone:
				angle, set_power = self.set_cruse()
			elif in_zone:
				angle, set_power = self.set_landing()
			mult = 1
			if self.abs_v_speed > self.landing_v_speed_max:
				power_offset += mult
				if angle > 0:
					angle -= 15
				elif angle < 0:
					angle += 15
			log([self.alt, self.safe_y])
			if (self.abs_v_speed < self.landing_v_speed_max and self.alt < 100) or (self.x in range(self.safe_x_min, self.safe_x_max) and self.v_speed >= 0):
				power_offset -= mult
			if self.alt < 100 and self.abs_h_speed < self.landing_h_speed_max:
				angle = 0
			self.update_craft(set_power+power_offset, angle)
			self.loop += 1

	def scan_terrain(self):
		surface_n = int(input())  # the number of points used to draw the surface of Mars.
		for i in range(surface_n):
			land_x, land_y = [int(j) for j in input().split()]
			self.hits.append([land_x, land_y])

	def update_telemetry(self, x, y, h_speed, v_speed, fuel, rotate, power):
		self.x = x
		self.y = y
		self.h_speed = h_speed
		self.v_speed = v_speed
		self.rotate = rotate
		self.power = power
		if abs(x - self.x_center) > self.total_distance:
			self.total_distance = abs(x - self.x_center)

		if fuel > self.total_fuel:
			self.total_fuel = fuel
		self.alt = abs(self.y-self.safe_y)
		self.normalized_fuel = fuel / self.total_fuel
		self.normalized_alt = y / (3000 - self.safe_y)
		self.remaining_dist_x = abs(x - self.x_center)
		self.normalized_dist = self.remaining_dist_x / self.total_distance
		if self.normalized_dist < 0.5:
			self.cruse_h_speed_max *= 0.8
			if self.cruse_h_speed_max < self.landing_h_speed_max:
				self.cruse_h_speed_max = self.landing_h_speed_max
		self.x_diff = self.x_center - x
		self.abs_h_speed = abs(h_speed)
		self.abs_v_speed = abs(v_speed)

	def update_craft(self, thrust, angle):
		if thrust > 4:
			thrust = 4
		if self.alt > 50 and thrust < 1:
			thrust = 1
		if thrust < 0:
			thrust = 0
		if angle > 90:
			angle = 90
		elif angle < -90:
			angle = -90
		log(["Updating craft to:", int(angle), int(thrust)])
		print(int(angle), int(thrust))

	def in_zone(self, x):
		if x in range(self.safe_x_min, self.safe_x_max) and self.alt < 500:
			log(['In zone', self.alt])
			return True
		else:
			log(['out zone', self.alt])
			return False

	def set_cruse(self):
		direction = self.get_direction_to_land()
		angle = self.rotate
		power_offset = 0
		if self.wait > 0:
			log(['Waiting... ', self.wait])
			self.wait -= 1
			return self.rotate, self.power
		if direction > 0:
			log('should be moving right')
			if self.rotate <= 0:
				log('rotate <= 0')
				# LEFT of center, rotation is RIGHT
				if self.h_speed == 0:
					angle = -45
					power_offset = 4
					self.wait = 3
					return angle, power_offset
				elif self.h_speed > 0:
					log('The speed is over 0')
					# Moving RIGHT
					if self.abs_h_speed <= self.cruse_h_speed_max:
						self.correcting_speed = False
						log('correct rotation, safe speed')
						if self.v_speed > 0 or self.above_peaks():
							power_offset = 3
						else:
							power_offset = 4
						if self.normalized_dist > 0.2 and self.abs_h_speed < self.landing_h_speed_max:
							angle = -45
						else:
							angle = 0
						return angle, power_offset
					if self.abs_h_speed > self.cruse_h_speed_max:
						log(['am i correcting speed? +', self.correcting_speed])
						if not self.correcting_speed:
							log('correcting speed +')
							angle = 30
							self.correction_angle = angle
							power_offset = 4
							self.correcting_speed = True
							return angle, power_offset
						else:
							return self.correction_angle, 4
				elif self.h_speed < 0:
					log('correct rotation, wrong speed vector')
					# Moving LEFT (wrong way)
					angle = -45
					power_offset = 4
					return angle, power_offset

			if self.rotate > 0:
				log('rotate > 0')
				# LEFT of center, rotation is RIGHT
				if self.h_speed == 0:
					angle = 45
					power_offset = 4
					self.wait = 3
					return angle, power_offset
				elif self.h_speed > 0:
					log('The speed is over 0')
					# Moving RIGHT
					if self.abs_h_speed <= self.cruse_h_speed_max:
						self.correcting_speed = False
						log('correct rotation, safe speed')
						angle = 0
						if self.v_speed < 0:
							power_offset = 3
						return angle, power_offset
					if self.abs_h_speed > self.cruse_h_speed_max:
						log(['am i correcting speed? - right', self.correcting_speed])
						if not self.correcting_speed:
							log('correcting speed -')
							angle = -30
							self.correction_angle = angle
							power_offset = 4
							self.correcting_speed = True
							return angle, power_offset
						else:
							return self.correction_angle, 4
				elif self.h_speed < 0:
					log('correct rotation, wrong speed vector')
					# Moving LEFT (wrong way)
					angle = -45
					power_offset = 4
					return angle, power_offset
		# SHOULD MOVE LEFT
		if direction < 0:
			log('Should be moving left')
			# Should be moving LEFT
			if self.rotate >= 0:
				# RIGHT of center, rotation is LEFT
				if self.h_speed == 0:
					angle = 45
					power_offset = 4
					self.wait = 3
					return angle, power_offset
				elif self.h_speed < 0:
					log('The speed is under 0')
					# Moving LEFT
					log(['my h speed vs the max', self.abs_h_speed, self.cruse_h_speed_max])
					if self.abs_h_speed <= self.cruse_h_speed_max:
						self.correcting_speed = False
						log('correct rotation, safe speed')
						if self.v_speed > 0 or self.above_peaks():
							power_offset = 3
						else:
							power_offset = 4
						if self.normalized_dist > 0.2 and self.abs_h_speed < self.landing_h_speed_max:
							angle = -45
						else:
							angle = 0
						return angle, power_offset
					if self.abs_h_speed > self.cruse_h_speed_max:
						log(['am i correcting speed? -', self.correcting_speed])
						if not self.correcting_speed:
							log('correcting speed -')
							angle = -30
							self.correction_angle = angle
							power_offset = 4
							self.correcting_speed = True
							return angle, power_offset
						else:
							return self.correction_angle, 4
				elif self.h_speed > 0:
					log('correct rotation, wrong speed vector')
					# Moving LEFT (wrong way)
					angle = 45
					power_offset = 4
					return angle, power_offset

			if self.rotate < 0:
				log('rotate > 0')
				# RIGHT of center, rotation is LEFT
				if self.h_speed == 0:
					angle = -45
					power_offset = 4
					self.wait = 3
					return angle, power_offset
				elif self.h_speed > 0:
					log('The speed is over 0')
					# Moving RIGHT
					if self.abs_h_speed <= self.cruse_h_speed_max:
						self.correcting_speed = False
						log('correct rotation, safe speed')

						angle = 0
						if self.v_speed < 0:
							power_offset = 3
						return angle, power_offset
					if self.abs_h_speed > self.cruse_h_speed_max:
						log(['am i correcting speed? - left', self.correcting_speed])
						if not self.correcting_speed:
							log('correcting speed -')
							angle = 30
							self.correction_angle = angle
							power_offset = 4
							self.correcting_speed = True
							return angle, power_offset
						else:
							return self.correction_angle, 4

				elif self.h_speed < 0:
					log('correct rotation, wrong speed vector')
					# Moving LEFT (wrong way)
					angle = 45
					power_offset = 4
					return angle, power_offset
		if direction == 0:
			return 0, 3
		log('FAILED TO SET COURSE')
		return angle, power_offset

	def set_landing(self):
		max_landing_angle = 8
		power_offset = 4
		angle = 0
		if self.h_speed < 0 and self.abs_h_speed > self.landing_h_speed_max:
			angle = (max_landing_angle*-1)*(self.abs_h_speed/self.landing_h_speed_max)
		elif self.h_speed > 0 and self.abs_h_speed > self.landing_h_speed_max:
			angle = max_landing_angle * (self.abs_h_speed / self.landing_h_speed_max)
		log(['abs h in range? ', self.abs_h_speed in range(0, self.landing_h_speed_max)])
		log(['v overspeed? ', self.abs_v_speed > self.landing_v_speed_max])
		if self.abs_h_speed in range(0, self.landing_h_speed_max) and self.abs_v_speed > self.landing_v_speed_max:
			if self.h_speed < 0:
				angle = -15
			if self.h_speed > 0:
				angle = 15
		if self.alt < 50:
			angle = 0
		return angle, power_offset

	def get_direction_to_land(self):
		if self.x < self.x_center:
			# Left of center, rotate should be - and h_speed should be +
			return 1
		elif self.x > self.x_center:
			return -1
		else:
			return 0

	def above_peaks(self):
		for x, y in self.hits:
			direction = self.get_direction_to_land()
			if direction > 0:
				big_x = self.x_center
				small_x = self.x
			else:
				big_x = self.x
				small_x = self.x_center
			log(['search range:', range(int(small_x), int(big_x)), 'center', self.x_center])
			if x in range(int(small_x), int(big_x)):
				tx = abs(x-self.x)
				ty = abs(y-self.y)
				terrain = intercept([tx, ty], [self.x, self.y])+200
				log(['y intercept', terrain, self.y, self.y > terrain])
				if self.y <= y+100 or self.y > terrain:
					log('Peak ahead!')
					return False
				else:
					return True


def slope(c1, c2):
	s = (c2[1]-c1[1])/(c2[0]-c1[0])
	return s


def intercept(c1, c2):
	i = (c1[1])-(slope(c1, c2)*c1[0])
	return i


def log(string):
	message = str(string)
	sys.stderr.write(message)
	print(file=sys.stderr)

Rover()

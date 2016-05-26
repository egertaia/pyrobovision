import configparser

#Reads the config
config = configparser.ConfigParser()
config.read('configs/cameras.conf')

#save_camera_config is a method that should write its config into the file
def save_camera_config(cameras):
	config = configparser.ConfigParser()
	config.read('configs/cameras.conf')

	for camera in cameras:
		config[camera.key] = {}
		config[camera.key]['LowerHue'] = str(camera.BALL_LOWER[0])
		config[camera.key]['LowerSaturation'] = str(camera.BALL_LOWER[1])
		config[camera.key]['LowerValue'] = str(camera.BALL_LOWER[2])
		config[camera.key]['HigherHue'] = str(camera.BALL_UPPER[0])
		config[camera.key]['HigherSaturation'] = str(camera.BALL_UPPER[1])
		config[camera.key]['HigherValue'] = str(camera.BALL_UPPER[2])

	with open('configs/cameras.conf', 'w') as configfile:
		config.write(configfile)

def load_camera_config(camera_map):
	config = configparser.ConfigParser()
	config.read('configs/cameras.conf')
	print(list(config.keys()))
	for key in config.keys():
		camera = camera_map.get(key)
		if camera:
			camera.BALL_LOWER[0] = int(config[key]['lowerhue'])
			camera.BALL_LOWER[1] = int(config[key]['lowersaturation'])
			camera.BALL_LOWER[2] = int(config[key]['lowervalue'])
			camera.BALL_UPPER[0] = int(config[key]['higherhue'])
			camera.BALL_UPPER[1] = int(config[key]['highersaturation'])
			camera.BALL_UPPER[2] = int(config[key]['highervalue'])



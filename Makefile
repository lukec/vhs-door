INSTALL_DIR=/usr/local/vhs/
ARDUINO_DIR=arduino_door_tweet
ARDUINO_SRC=$(ARDUINO_DIR)/arduino_door_tweet.pde
ARDUINO_HEX=$(ARDUINO_DIR)/applet/arduino_door_tweet.hex
HOOKS_SRC=$(wildcard hooks/*.d/*)
DAEMON=$(bin/arduino-daemon)
LIBS=$(wildcard lib/*)
WWW_ROOT=/var/www

$(ARDUINO_HEX): $(ARDUINO_SRC)
	sudo pkill arduino-daemon
	cd $(ARDUINO_DIR) && make && make upload

install: $(HOOKS_SRC) $(DAEMON) $(LIBS)
	cp -R hooks $(INSTALL_DIR)
	cp -R bin $(INSTALL_DIR)
	cp -R lib $(INSTALL_DIR)
	# setup sensor web server
	install -o www-data -g www-data -m 755 -d $(WWW_ROOT)/sensor
	install -o www-data -g www-data -p -m 755 sensor/www/sensor.py $(WWW_ROOT)/sensor
	install -o www-data -g www-data -p -m 755 sensor/www/decorators.py $(WWW_ROOT)/sensor
	# update serial server and startup script
	install -o nobody -g dialout -p -m 755 sensor/serialserver.py $(INSTALL_DIR)bin
	install sensor/serialserverd /etc/init.d

release: $(ARDUINO_HEX)
	make install
	$(INSTALL_DIR)/bin/restart-daemon

clean:
	cd $(ARDUINO_DIR) && make clean

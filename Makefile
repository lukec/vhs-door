INSTALL_DIR=/usr/local/vhs/
ARDUINO_DIR=arduino_door_tweet
ARDUINO_SRC=$(ARDUINO_DIR)/arduino_door_tweet.pde
ARDUINO_HEX=$(ARDUINO_DIR)/applet/arduino_door_tweet.hex
HOOKS_SRC=$(wildcard hooks/*.d/*)
DAEMON=$(bin/arduino-daemon)
LIBS=$(wildcard lib/*)

$(ARDUINO_HEX): $(ARDUINO_SRC)
	sudo pkill arduino-daemon
	cd $(ARDUINO_DIR) && make && make upload

install: $(HOOKS_SRC) $(DAEMON) $(LIBS)
	cp -R hooks $(INSTALL_DIR)
	cp -R bin $(INSTALL_DIR)
	cp -R lib $(INSTALL_DIR)

release: $(ARDUINO_HEX)
	make install
	$(INSTALL_DIR)/bin/restart-daemon

clean:
	cd $(ARDUINO_DIR) && make clean

.PHONY: format format-check analyze test package-test ios-build android-build run

run:
	NO_PROXY="localhost,127.0.0.1,::1" no_proxy="localhost,127.0.0.1,::1" flutter run

format:
	dart format .

format-check:
	dart format --output=none --set-exit-if-changed .

analyze:
	flutter analyze

test:
	flutter test

package-test:
	flutter test packages/*/test

ios-build:
	flutter build ios --no-codesign

android-build:
	flutter build apk --debug

.PHONY: format format-check analyze test package-test ios-build android-build

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

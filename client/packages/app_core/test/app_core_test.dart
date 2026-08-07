import 'package:app_core/app_core.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('uses the local development API by default', () {
    final client = RedBookEditorApiClient();
    expect(client.baseUrl, 'http://127.0.0.1:8000');
  });
}

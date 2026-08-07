import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'content_workflow_models.dart';

class SourceExperienceDraftStore {
  SourceExperienceDraftStore({SharedPreferencesAsync? preferences})
    : _preferences = preferences ?? SharedPreferencesAsync();

  static const _key = 'source_experience_draft';
  final SharedPreferencesAsync _preferences;

  Future<void> save(SourceExperience source) =>
      _preferences.setString(_key, jsonEncode(source.toJson()));

  Future<SourceExperience?> load() async {
    final value = await _preferences.getString(_key);
    if (value == null) return null;
    final json = jsonDecode(value) as Map<String, dynamic>;
    return SourceExperience.fromJson(json);
  }

  Future<void> clear() => _preferences.remove(_key);
}

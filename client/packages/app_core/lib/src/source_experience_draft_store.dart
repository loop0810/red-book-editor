import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'content_workflow_models.dart';

class SourceExperienceDraftStore {
  SourceExperienceDraftStore({SharedPreferencesAsync? preferences})
    : _preferences = preferences ?? SharedPreferencesAsync();

  static const _key = 'source_experience_draft';
  final SharedPreferencesAsync _preferences;

  // 请求前先把事实输入保存在设备上；模型请求失败时，页面可以从这里恢复。
  Future<void> save(SourceExperience source) =>
      _preferences.setString(_key, jsonEncode(source.toJson()));

  Future<SourceExperience?> load() async {
    // 存储层只保存 JSON 字符串，恢复后立刻转换回 SourceExperience，
    // 让上层不需要处理 SharedPreferences 的细节。
    final value = await _preferences.getString(_key);
    if (value == null) return null;
    final json = jsonDecode(value) as Map<String, dynamic>;
    return SourceExperience.fromJson(json);
  }

  // 只有生成成功并把内容交给编辑器后才清理，避免失败请求造成数据丢失。
  Future<void> clear() => _preferences.remove(_key);
}

class ContentBriefDraftStore {
  ContentBriefDraftStore({SharedPreferencesAsync? preferences})
    : _preferences = preferences ?? SharedPreferencesAsync();

  static const _key = 'content_brief_draft';
  final SharedPreferencesAsync _preferences;

  Future<void> save(ContentBrief brief) =>
      _preferences.setString(_key, jsonEncode(brief.toJson()));

  Future<ContentBrief?> load() async {
    final value = await _preferences.getString(_key);
    if (value == null) return null;
    return ContentBrief.fromJson(jsonDecode(value) as Map<String, dynamic>);
  }

  Future<void> clear() => _preferences.remove(_key);
}

import 'package:app_core/app_core.dart';

typedef GenerateNote = Future<NoteDraft> Function(SourceExperience source);
typedef UploadAsset = Future<String> Function(String filePath);
typedef RegenerateField =
    Future<NoteDraft> Function(NoteDraft draft, String field);
typedef SaveDraft = Future<NoteDraft> Function(NoteDraft draft);
typedef LoadVersions = Future<List<NoteDraftVersion>> Function(String noteId);
typedef OpenDraft = Future<void> Function(NoteDraft draft);

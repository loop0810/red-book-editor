import 'package:app_core/app_core.dart';

typedef GenerateNote =
    Future<StyledNoteResponse> Function(
      SourceExperience source,
      StyleForm form,
    );
typedef UploadAsset = Future<String> Function(String filePath);
typedef RegenerateField =
    Future<NoteDraft> Function(
      NoteDraft draft,
      String field, {
      StyleForm? form,
    });
typedef SaveDraft = Future<NoteDraft> Function(NoteDraft draft);
typedef LoadVersions = Future<List<NoteDraftVersion>> Function(String noteId);
typedef OpenDraft = Future<void> Function(NoteDraft draft);

import 'package:app_core/app_core.dart';

// Feature package 通过这些 typedef 接收能力，而不是依赖具体页面或 API 实现。
// main.dart 负责把真实实现注入进来，测试可以传入 fake 函数。
typedef GenerateNote =
    Future<StyledNoteResponse> Function(
      SourceExperience source,
      StyleForm form,
    );
typedef GenerateNoteWithProgress =
    Future<StyledNoteResponse> Function(
      SourceExperience source,
      StyleForm form, {
      void Function(AgentRunEvent event)? onEvent,
      void Function(AgentRun run)? onRunCreated,
    });
typedef CancelAgentRun = Future<AgentRun> Function(String runId);
typedef ResumeAgentRun =
    Future<StyledNoteResponse> Function(
      String runId, {
      void Function(AgentRunEvent event)? onEvent,
      void Function(AgentRun run)? onRunCreated,
    });
typedef UploadAsset = Future<String> Function(String filePath);

// field 是 title/body/hashtags/cover_copy 之一，服务端据此执行局部更新。
typedef RegenerateField =
    Future<FieldSuggestion> Function(
      NoteDraft draft,
      String field, {
      StyleForm? form,
    });
typedef SaveDraft = Future<NoteDraft> Function(NoteDraft draft);
typedef LoadSuggestions = Future<List<FieldSuggestion>> Function(String noteId);
typedef UpdateSuggestionStatus =
    Future<FieldSuggestion> Function(
      FieldSuggestion suggestion,
      SuggestionStatus status,
    );

// 版本读取和草稿打开也用回调隔离，页面无需知道数据来自 SQLite、API 还是内存。
typedef LoadVersions = Future<List<NoteDraftVersion>> Function(String noteId);
typedef OpenDraft = Future<void> Function(NoteDraft draft);

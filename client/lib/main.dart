import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:note_creation/note_creation.dart';
import 'package:account_workspace/account_workspace.dart';
import 'package:asset_library/asset_library.dart';
import 'package:publish_records/publish_records.dart';

// Riverpod 在这里负责把“如何创建 API Client”注入页面。
// 页面只需要 ref.read(apiClientProvider)，不需要自己管理 http.Client 的生命周期。
final apiClientProvider = Provider<RedBookEditorApiClient>(
  (ref) => RedBookEditorApiClient(),
);

const _accountId = '00000000-0000-0000-0000-000000000001';
const _defaultColumnId = '00000000-0000-0000-0000-000000000002';

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const WorkbenchHomePage()),
  ],
);

void main() {
  // ProviderScope 是 Riverpod 的根容器；放在最外层后，下面所有页面都能读取 provider。
  runApp(const ProviderScope(child: RedBookEditorApp()));
}

class RedBookEditorApp extends StatelessWidget {
  const RedBookEditorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '小红书内容工作台',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.red),
      ),
      routerConfig: _router,
    );
  }
}

class WorkbenchHomePage extends ConsumerWidget {
  const WorkbenchHomePage({super.key});

  Future<void> _openEditor(
    BuildContext context,
    WidgetRef ref,
    NoteDraft draft,
  ) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => NoteEditorPage(
          draft: draft,
          onRegenerateField: (current, field, {form}) => ref
              .read(apiClientProvider)
              .regenerateField(draft: current, field: field, form: form),
          onSaveDraft: (current) =>
              ref.read(apiClientProvider).saveNote(draft: current),
          loadVersions: (noteId) =>
              ref.read(apiClientProvider).listNoteVersions(noteId: noteId),
          onPublish: () => _openPublishRecord(context, ref, draft),
        ),
      ),
    );
  }

  Future<void> _openPublishRecord(
    BuildContext context,
    WidgetRef ref,
    NoteDraft draft,
  ) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PublishRecordPage(
          onSave: ({required status, link, views, likes, saves, comments}) =>
              ref
                  .read(apiClientProvider)
                  .recordPublication(
                    noteId: draft.noteId,
                    status: status,
                    link: link,
                    views: views,
                    likes: likes,
                    saves: saves,
                    comments: comments,
                  ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('小红书内容工作台')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            FilledButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => NoteCreationPage(
                      generate: (source, form) => ref
                          .read(apiClientProvider)
                          // 这里是客户端主链路的起点：页面表单产生 source/form，
                          // API Client 将它们编码成 POST /notes/generate 请求。
                          .generateNote(
                            accountId: _accountId,
                            columnId: _defaultColumnId,
                            source: source,
                            form: form,
                          ),
                      generateWithProgress:
                          (source, form, {onEvent, onRunCreated}) => ref
                              .read(apiClientProvider)
                              .generateNoteWithProgress(
                                accountId: _accountId,
                                columnId: _defaultColumnId,
                                source: source,
                                form: form,
                                onEvent: onEvent,
                                onRunCreated: onRunCreated,
                              ),
                      resumeAgentRun: (runId, {onEvent, onRunCreated}) => ref
                          .read(apiClientProvider)
                          .resumeAgentRunWithProgress(
                            runId: runId,
                            onEvent: onEvent,
                            onRunCreated: onRunCreated,
                          ),
                      cancelAgentRun: (runId) => ref
                          .read(apiClientProvider)
                          .cancelAgentRun(runId: runId),
                      uploadAsset: (filePath) => ref
                          .read(apiClientProvider)
                          .uploadAsset(
                            accountId: _accountId,
                            filePath: filePath,
                          ),
                      onDraftGenerated: (response, selectedForm) async {
                        // 服务端返回的是 StyledNoteResponse：draft 是可编辑内容，
                        // agentTrace 是可展示的执行摘要；两者一起交给编辑器页面。
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => NoteEditorPage(
                              draft: response.draft,
                              aiBaseline: response.draft,
                              agentTrace: response.agentTrace,
                              styleForm: selectedForm,
                              onRegenerateField: (current, field, {form}) => ref
                                  .read(apiClientProvider)
                                  .regenerateField(
                                    draft: current,
                                    field: field,
                                    form: form,
                                  ),
                              onSaveDraft: (current) => ref
                                  .read(apiClientProvider)
                                  .saveNote(draft: current),
                              loadVersions: (noteId) => ref
                                  .read(apiClientProvider)
                                  .listNoteVersions(noteId: noteId),
                              onPublish: () => _openPublishRecord(
                                context,
                                ref,
                                response.draft,
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.add),
              label: const Text('新建育儿笔记'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => DraftListPage(
                    listDrafts: () => ref
                        .read(apiClientProvider)
                        .listNotes(accountId: _accountId),
                    onOpenDraft: (draft) => _openEditor(context, ref, draft),
                  ),
                ),
              ),
              icon: const Icon(Icons.article_outlined),
              label: const Text('草稿列表'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => AssetLibraryPage(
                    listAssets: () => ref
                        .read(apiClientProvider)
                        .listAssets(accountId: _accountId),
                    uploadAsset: (filePath, onProgress) => ref
                        .read(apiClientProvider)
                        .uploadAsset(
                          accountId: _accountId,
                          filePath: filePath,
                          onProgress: onProgress,
                        ),
                    deleteAsset: (assetId) => ref
                        .read(apiClientProvider)
                        .deleteAsset(assetId: assetId),
                    reorderAssets: (assetIds) => ref
                        .read(apiClientProvider)
                        .reorderAssets(
                          accountId: _accountId,
                          assetIds: assetIds,
                        ),
                    downloadAsset: (assetId) => ref
                        .read(apiClientProvider)
                        .downloadAsset(assetId: assetId),
                    exportImage: (bytes, filename) =>
                        const GalleryExportService().saveImage(
                          bytes: bytes,
                          filename: filename,
                        ),
                  ),
                ),
              ),
              icon: const Icon(Icons.photo_library_outlined),
              label: const Text('图片素材'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AccountWorkspacePage()),
              ),
              icon: const Icon(Icons.settings),
              label: const Text('账号配置'),
            ),
          ],
        ),
      ),
    );
  }
}

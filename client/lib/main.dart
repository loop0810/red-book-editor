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

final accountsProvider = FutureProvider<List<AccountProfile>>(
  (ref) => ref.read(apiClientProvider).listAccounts(),
);

final columnsProvider = FutureProvider.family<List<ContentColumn>, String>(
  (ref, accountId) =>
      ref.read(apiClientProvider).listColumns(accountId: accountId),
);

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const WorkbenchHomePage()),
  ],
);

void main() {
  // ProviderScope 是 Riverpod 的根容器；放在最外层后，下面所有页面都能读取 provider。
  runApp(const RedBookEditorApp());
}

class RedBookEditorApp extends StatelessWidget {
  const RedBookEditorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: MaterialApp.router(
        title: '小红书内容工作台',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.red),
        ),
        routerConfig: _router,
      ),
    );
  }
}

class WorkbenchHomePage extends ConsumerStatefulWidget {
  const WorkbenchHomePage({super.key});

  @override
  ConsumerState<WorkbenchHomePage> createState() => _WorkbenchHomePageState();
}

class _WorkbenchHomePageState extends ConsumerState<WorkbenchHomePage> {
  String? _selectedAccountId;
  String? _selectedColumnId;

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
          loadSuggestions: (noteId) =>
              ref.read(apiClientProvider).listSuggestions(noteId: noteId),
          onUpdateSuggestionStatus: (suggestion, status) => ref
              .read(apiClientProvider)
              .updateSuggestionStatus(
                noteId: suggestion.noteId,
                suggestionId: suggestion.suggestionId,
                status: status,
              ),
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
  Widget build(BuildContext context) {
    final accounts = ref.watch(accountsProvider);
    if (accounts.isLoading) {
      return const Scaffold(
        appBar: _WorkbenchAppBar(),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (accounts.hasError || accounts.valueOrNull == null) {
      return const Scaffold(
        appBar: _WorkbenchAppBar(),
        body: Center(child: Text('暂时无法读取账号配置，请稍后重试')),
      );
    }
    final account =
        accounts.value!
            .where((item) => item.accountId == _selectedAccountId)
            .firstOrNull ??
        (accounts.value!.isEmpty ? null : accounts.value!.first);
    if (account == null) {
      return Scaffold(
        appBar: const _WorkbenchAppBar(),
        body: _EmptyAccountState(
          onCreate: () => _openFirstAccountSetup(context, ref),
        ),
      );
    }
    final columns = ref.watch(columnsProvider(account.accountId));
    if (columns.isLoading) {
      return const Scaffold(
        appBar: _WorkbenchAppBar(),
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (columns.hasError || columns.valueOrNull == null) {
      return const Scaffold(
        appBar: _WorkbenchAppBar(),
        body: Center(child: Text('暂时无法读取账号栏目，请稍后重试')),
      );
    }
    final column =
        columns.value!
            .where((item) => item.columnId == _selectedColumnId)
            .firstOrNull ??
        (columns.value!.isEmpty ? null : columns.value!.first);
    if (column == null) {
      return Scaffold(
        appBar: const _WorkbenchAppBar(),
        body: _EmptyColumnState(
          onCreate: () => _createDefaultColumn(context, ref, account.accountId),
        ),
      );
    }
    final accountId = account.accountId;
    final columnId = column.columnId;
    return Scaffold(
      appBar: AppBar(title: const Text('小红书内容工作台')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            DropdownButtonFormField<String>(
              initialValue: account.accountId,
              decoration: const InputDecoration(labelText: '账号'),
              items: [
                for (final item in accounts.value!)
                  DropdownMenuItem(
                    value: item.accountId,
                    child: Text(item.positioning),
                  ),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() {
                  _selectedAccountId = value;
                  _selectedColumnId = null;
                });
              },
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: column.columnId,
              decoration: const InputDecoration(labelText: '栏目'),
              items: [
                for (final item in columns.value!)
                  DropdownMenuItem(
                    value: item.columnId,
                    child: Text(item.name),
                  ),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() => _selectedColumnId = value);
              },
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => NoteCreationPage(
                      generate: (contentBrief, form) => ref
                          .read(apiClientProvider)
                          // 这里是客户端主链路的起点：页面表单产生 ContentBrief/form，
                          // API Client 将它们编码成 POST /notes/generate 请求。
                          .generateNote(
                            accountId: accountId,
                            columnId: columnId,
                            contentBrief: contentBrief,
                            form: form,
                          ),
                      generateWithProgress:
                          (contentBrief, form, {onEvent, onRunCreated}) => ref
                              .read(apiClientProvider)
                              .generateNoteWithProgress(
                                accountId: accountId,
                                columnId: columnId,
                                contentBrief: contentBrief,
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
                            accountId: accountId,
                            filePath: filePath,
                          ),
                      onDraftGenerated: (response, selectedForm) async {
                        // 服务端返回的是 StyledNoteResponse：draft 是可编辑内容，
                        // 只把用户结果交给编辑器；运行 trace 留在服务端内部诊断。
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => NoteEditorPage(
                              draft: response.draft,
                              aiBaseline: response.draft,
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
                              loadSuggestions: (noteId) => ref
                                  .read(apiClientProvider)
                                  .listSuggestions(noteId: noteId),
                              onUpdateSuggestionStatus: (suggestion, status) =>
                                  ref
                                      .read(apiClientProvider)
                                      .updateSuggestionStatus(
                                        noteId: suggestion.noteId,
                                        suggestionId: suggestion.suggestionId,
                                        status: status,
                                      ),
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
              label: const Text('新建内容'),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => DraftListPage(
                    listDrafts: () => ref
                        .read(apiClientProvider)
                        .listNotes(accountId: accountId),
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
                        .listAssets(accountId: accountId),
                    uploadAsset: (filePath, onProgress) => ref
                        .read(apiClientProvider)
                        .uploadAsset(
                          accountId: accountId,
                          filePath: filePath,
                          onProgress: onProgress,
                        ),
                    deleteAsset: (assetId) => ref
                        .read(apiClientProvider)
                        .deleteAsset(assetId: assetId),
                    reorderAssets: (assetIds) => ref
                        .read(apiClientProvider)
                        .reorderAssets(
                          accountId: accountId,
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
                MaterialPageRoute(
                  builder: (_) => AccountWorkspacePage(
                    accountId: account.accountId,
                    domainId: account.domainId,
                    initialPositioning: account.positioning,
                    initialTone: account.tone,
                    initialBabyMonth: account.currentBabyMonth ?? 19,
                    onSave:
                        ({
                          required accountId,
                          required positioning,
                          required tone,
                          required currentBabyMonth,
                        }) async {
                          await ref
                              .read(apiClientProvider)
                              .updateAccount(
                                account: AccountProfile(
                                  accountId: account.accountId,
                                  domainId: account.domainId,
                                  positioning: positioning,
                                  tone: tone,
                                  domainContext: account.domainContext,
                                  currentBabyMonth: currentBabyMonth,
                                  boundaries: account.boundaries,
                                  commonExpressions: account.commonExpressions,
                                ),
                              );
                          ref.invalidate(accountsProvider);
                        },
                  ),
                ),
              ),
              icon: const Icon(Icons.settings),
              label: const Text('账号配置'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _openFirstAccountSetup(
    BuildContext context,
    WidgetRef ref,
  ) async {
    AccountProfile? createdAccount;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AccountWorkspacePage(
          accountId: null,
          domainId: 'parenting',
          initialPositioning: '记录真实育儿生活',
          initialTone: '真实、自然、少一点说教',
          initialBabyMonth: 0,
          onSave:
              ({
                required accountId,
                required positioning,
                required tone,
                required currentBabyMonth,
              }) async {
                final api = ref.read(apiClientProvider);
                createdAccount ??= await api.createAccount(
                  account: AccountProfile(
                    accountId: '',
                    domainId: 'parenting',
                    positioning: positioning,
                    tone: tone,
                    currentBabyMonth: currentBabyMonth,
                  ),
                );
                await api.createColumn(
                  accountId: createdAccount!.accountId,
                  name: '日常分享',
                  description: '记录真实经历与实用经验',
                  contentTypes: const ['note'],
                );
                ref.invalidate(accountsProvider);
              },
        ),
      ),
    );
  }

  Future<void> _createDefaultColumn(
    BuildContext context,
    WidgetRef ref,
    String accountId,
  ) async {
    try {
      await ref
          .read(apiClientProvider)
          .createColumn(
            accountId: accountId,
            name: '日常分享',
            description: '记录真实经历与实用经验',
            contentTypes: const ['note'],
          );
      ref.invalidate(columnsProvider(accountId));
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('创建栏目失败：$error')));
    }
  }
}

class _EmptyAccountState extends StatelessWidget {
  const _EmptyAccountState({required this.onCreate});

  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('还没有配置账号'),
          const SizedBox(height: 8),
          const Text('当前版本是本地内容工作台，无需注册或登录。先配置账号定位即可开始创作。'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onCreate,
            icon: const Icon(Icons.person_add_alt_1),
            label: const Text('配置第一个账号'),
          ),
        ],
      ),
    ),
  );
}

class _EmptyColumnState extends StatelessWidget {
  const _EmptyColumnState({required this.onCreate});

  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('账号还没有内容栏目'),
          const SizedBox(height: 8),
          const Text('创建一个默认栏目后，就可以开始生成内容。'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onCreate,
            icon: const Icon(Icons.add),
            label: const Text('创建默认栏目'),
          ),
        ],
      ),
    ),
  );
}

class _WorkbenchAppBar extends StatelessWidget implements PreferredSizeWidget {
  const _WorkbenchAppBar();

  @override
  Widget build(BuildContext context) => AppBar(title: const Text('小红书内容工作台'));

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);
}

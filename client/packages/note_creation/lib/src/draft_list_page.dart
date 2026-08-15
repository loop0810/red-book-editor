import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';

import 'note_creation_types.dart';

class DraftListPage extends StatefulWidget {
  const DraftListPage({
    required this.listDrafts,
    required this.onOpenDraft,
    super.key,
  });

  final Future<List<NoteDraft>> Function() listDrafts;
  final OpenDraft onOpenDraft;

  @override
  State<DraftListPage> createState() => _DraftListPageState();
}

class _DraftListPageState extends State<DraftListPage> {
  List<NoteDraft>? _drafts;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final drafts = await widget.listDrafts();
      if (mounted) setState(() => _drafts = drafts);
    } catch (error) {
      if (mounted) setState(() => _error = '草稿列表加载失败：$error');
    }
  }

  String _titleOf(NoteDraft draft) {
    if (draft.titleCandidates.isNotEmpty) return draft.titleCandidates.first;
    if (draft.topicAngle.isNotEmpty) return draft.topicAngle;
    return draft.source.scenario;
  }

  String _statusLabel(NoteStatus status) {
    switch (status) {
      case NoteStatus.draft:
        return '草稿';
      case NoteStatus.needsReview:
        return '待复核';
      case NoteStatus.ready:
        return '可复制';
      case NoteStatus.published:
        return '已发布';
      case NoteStatus.discarded:
        return '不发布';
    }
  }

  String _reviewLabel(NoteDraft draft) {
    if (draft.reviewFindings.isEmpty) return '';
    final hasBlocking = draft.reviewFindings.any(
      (finding) => finding.level == RiskLevel.blocking,
    );
    return hasBlocking ? '有阻断风险' : '有审核提示';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('草稿列表'),
        actions: [
          IconButton(
            tooltip: '刷新',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Builder(
        builder: (context) {
          if (_error != null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text(_error!),
              ),
            );
          }
          final drafts = _drafts;
          if (drafts == null) {
            return const Center(child: CircularProgressIndicator());
          }
          if (drafts.isEmpty) {
            return const Center(child: Text('还没有草稿，先去记录一次育儿经历吧'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: drafts.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final draft = drafts[index];
              return Card(
                child: ListTile(
                  title: Text(
                    _titleOf(draft),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    [
                      if (draft.styleForm != null)
                        '表达形式：${styleFormDisplayName(draft.styleForm!)}',
                      if (_reviewLabel(draft).isNotEmpty) _reviewLabel(draft),
                      draft.body.isEmpty ? draft.source.scenario : draft.body,
                    ].join(' · '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Chip(
                        label: Text(_statusLabel(draft.status)),
                        visualDensity: VisualDensity.compact,
                      ),
                      Text(
                        draft.updatedAt,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                  onTap: () => widget.onOpenDraft(draft),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

import 'dart:io';

import 'package:app_core/app_core.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'note_creation_types.dart';
import 'note_editor_page.dart';

class NoteCreationPage extends StatefulWidget {
  // 页面只负责收集输入和管理交互；真正的生成函数由外层 main.dart 注入。
  // 这样 feature package 不需要知道 API Client 或具体网络实现。
  const NoteCreationPage({
    required this.generate,
    this.generateWithProgress,
    this.cancelAgentRun,
    this.uploadAsset,
    this.onDraftGenerated,
    super.key,
  });

  final GenerateNote generate;
  final GenerateNoteWithProgress? generateWithProgress;
  final CancelAgentRun? cancelAgentRun;
  final UploadAsset? uploadAsset;
  final Future<void> Function(StyledNoteResponse response, StyleForm form)?
  onDraftGenerated;

  @override
  State<NoteCreationPage> createState() => _NoteCreationPageState();
}

class _NoteCreationPageState extends State<NoteCreationPage> {
  // Controller 保存输入框内容，_draftStore 保存“请求尚未完成时”的本地草稿。
  final _scenarioController = TextEditingController();
  final _actionsController = TextEditingController();
  final _observationsController = TextEditingController();
  final _notesController = TextEditingController();
  final _picker = ImagePicker();
  final _pickedPaths = <String>[];
  int _babyMonth = 19;
  StyleForm _selectedForm = StyleForm.experience;
  bool _loading = false;
  String? _error;
  String? _activeRunId;
  String? _agentPhase;
  String? _agentSummary;
  final _draftStore = SourceExperienceDraftStore();

  @override
  void initState() {
    super.initState();
    // 页面重新打开时先恢复上次未完成的 SourceExperience。
    _restoreDraft();
  }

  Future<void> _restoreDraft() async {
    // 恢复草稿是异步的，所以回写 UI 前必须确认 State 仍挂在 widget tree 上。
    final draft = await _draftStore.load();
    if (!mounted || draft == null) return;
    _scenarioController.text = draft.scenario;
    _actionsController.text = draft.actions.join('，');
    _observationsController.text = draft.observations;
    _notesController.text = draft.notes;
    setState(() {
      _babyMonth = draft.babyMonth;
      _pickedPaths
        ..clear()
        ..addAll(draft.assetIds);
    });
  }

  Future<void> _pickImages() async {
    // 图片此时只有本地路径；点击生成时才会通过 widget.uploadAsset 上传到服务端。
    final picked = await _picker.pickMultiImage(imageQuality: 90);
    if (!mounted) return;
    setState(() {
      _pickedPaths.addAll(picked.map((file) => file.path));
    });
  }

  void _removeImage(int index) {
    setState(() => _pickedPaths.removeAt(index));
  }

  @override
  void dispose() {
    _scenarioController.dispose();
    _actionsController.dispose();
    _observationsController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    // 生成主链路：校验输入 → 上传素材 → 组装 SourceExperience → 保存本地草稿 → 请求 Agent。
    // 在请求成功前不清除本地草稿，避免网络或模型失败导致用户输入丢失。
    if (_scenarioController.text.trim().isEmpty ||
        _actionsController.text.trim().isEmpty) {
      setState(() => _error = '请先填写发生了什么和你做了什么');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final assetIds = <String>[];
      for (final path in _pickedPaths) {
        if (widget.uploadAsset == null) {
          assetIds.add(path);
          continue;
        }
        assetIds.add(await widget.uploadAsset!(path));
      }
      final source = SourceExperience(
        babyMonth: _babyMonth,
        scenario: _scenarioController.text.trim(),
        actions: _actionsController.text
            .split(RegExp(r'[,，\n]'))
            .map((action) => action.trim())
            .where((action) => action.isNotEmpty)
            .toList(),
        observations: _observationsController.text.trim(),
        notes: _notesController.text.trim(),
        assetIds: assetIds,
      );
      await _draftStore.save(source);
      // generate 是依赖注入进来的 Future：测试时可以替换成 fake，生产时由 API Client 实现。
      final response = widget.generateWithProgress == null
          ? await widget.generate(source, _selectedForm)
          : await widget.generateWithProgress!(
              source,
              _selectedForm,
              onRunCreated: (run) {
                if (!mounted) return;
                setState(() {
                  _activeRunId = run.runId;
                  _agentPhase = run.currentPhase;
                });
              },
              onEvent: (event) {
                if (!mounted) return;
                setState(() {
                  _agentPhase = event.phase;
                  _agentSummary = event.summary;
                });
              },
            );
      _activeRunId = null;
      await _draftStore.clear();
      // 只有服务端生成成功才进入编辑器；response 同时携带 draft 和 agentTrace。
      if (mounted) {
        if (widget.onDraftGenerated != null) {
          await widget.onDraftGenerated!(response, _selectedForm);
        } else {
          await Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => NoteEditorPage(
                draft: response.draft,
                agentTrace: response.agentTrace,
                styleForm: _selectedForm,
              ),
            ),
          );
        }
      }
    } catch (error) {
      if (mounted) setState(() => _error = '生成失败：$error');
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _activeRunId = null;
        });
      }
    }
  }

  Future<void> _cancelGeneration() async {
    final runId = _activeRunId;
    if (runId == null || widget.cancelAgentRun == null) return;
    try {
      await widget.cancelAgentRun!(runId);
      if (mounted) setState(() => _error = '已请求取消生成');
    } catch (error) {
      if (mounted) setState(() => _error = '取消失败：$error');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('记录一次育儿经历')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('宝宝月龄：$_babyMonth 个月'),
          Slider(
            value: _babyMonth.toDouble(),
            min: 0,
            max: 24,
            divisions: 24,
            onChanged: (value) => setState(() => _babyMonth = value.round()),
          ),
          TextField(
            controller: _scenarioController,
            decoration: const InputDecoration(labelText: '发生了什么'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _actionsController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '我做了什么（可用逗号分隔）'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _observationsController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '观察到什么变化'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            maxLines: 3,
            decoration: const InputDecoration(labelText: '补充说明'),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: _pickImages,
                icon: const Icon(Icons.photo_library),
                label: const Text('选择图片（可选）'),
              ),
              if (_pickedPaths.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(left: 12),
                  child: Text('已选 ${_pickedPaths.length} 张'),
                ),
            ],
          ),
          if (_pickedPaths.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var index = 0; index < _pickedPaths.length; index++)
                  Stack(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(
                          File(_pickedPaths[index]),
                          width: 80,
                          height: 80,
                          fit: BoxFit.cover,
                          errorBuilder: (_, _, _) => const SizedBox.square(
                            dimension: 80,
                            child: Icon(Icons.image),
                          ),
                        ),
                      ),
                      Positioned(
                        top: 0,
                        right: 0,
                        child: InkWell(
                          onTap: () => _removeImage(index),
                          child: Container(
                            decoration: const BoxDecoration(
                              color: Colors.black54,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.close,
                              size: 16,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          Text('表达形式', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          SegmentedButton<StyleForm>(
            segments: const [
              ButtonSegment(value: StyleForm.popularScience, label: Text('科普')),
              ButtonSegment(value: StyleForm.experience, label: Text('经验')),
              ButtonSegment(value: StyleForm.advertorial, label: Text('软文')),
            ],
            selected: {_selectedForm},
            onSelectionChanged: (selection) {
              setState(() => _selectedForm = selection.first);
            },
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _loading ? null : _generate,
            icon: _loading
                ? const SizedBox.square(
                    dimension: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.auto_awesome),
            label: Text(_loading ? '生成中…' : '生成笔记'),
          ),
          if (_loading && widget.generateWithProgress != null) ...[
            const SizedBox(height: 12),
            Text(
              [
                if (_agentPhase != null) '阶段：$_agentPhase',
                ?_agentSummary,
              ].join(' · '),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (_activeRunId != null && widget.cancelAgentRun != null)
              TextButton.icon(
                onPressed: _cancelGeneration,
                icon: const Icon(Icons.stop_circle_outlined),
                label: const Text('取消生成'),
              ),
          ],
        ],
      ),
    );
  }
}

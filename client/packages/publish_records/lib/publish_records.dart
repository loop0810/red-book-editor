import 'package:flutter/material.dart';

class PublishRecordPage extends StatefulWidget {
  const PublishRecordPage({required this.onSave, super.key});

  final Future<void> Function({
    required String status,
    String? link,
    int? views,
    int? likes,
    int? saves,
    int? comments,
  })
  onSave;

  @override
  State<PublishRecordPage> createState() => _PublishRecordPageState();
}

class _PublishRecordPageState extends State<PublishRecordPage> {
  final _linkController = TextEditingController();
  final _viewsController = TextEditingController();
  final _likesController = TextEditingController();
  final _savesController = TextEditingController();
  final _commentsController = TextEditingController();
  String _status = 'published';
  bool _saving = false;

  @override
  void dispose() {
    _linkController.dispose();
    _viewsController.dispose();
    _likesController.dispose();
    _savesController.dispose();
    _commentsController.dispose();
    super.dispose();
  }

  int? _number(TextEditingController controller) =>
      int.tryParse(controller.text.trim());

  Future<void> _save() async {
    setState(() => _saving = true);
    await widget.onSave(
      status: _status,
      link: _linkController.text.trim().isEmpty
          ? null
          : _linkController.text.trim(),
      views: _number(_viewsController),
      likes: _number(_likesController),
      saves: _number(_savesController),
      comments: _number(_commentsController),
    );
    if (mounted) {
      setState(() => _saving = false);
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('记录发布结果')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          DropdownButtonFormField<String>(
            initialValue: _status,
            decoration: const InputDecoration(labelText: '发布状态'),
            items: const [
              DropdownMenuItem(value: 'published', child: Text('已发布')),
              DropdownMenuItem(value: 'discarded', child: Text('不发布')),
            ],
            onChanged: (value) =>
                setState(() => _status = value ?? 'published'),
          ),
          TextField(
            controller: _linkController,
            decoration: const InputDecoration(labelText: '笔记链接（可选）'),
          ),
          TextField(
            controller: _viewsController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '浏览量'),
          ),
          TextField(
            controller: _likesController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '点赞'),
          ),
          TextField(
            controller: _savesController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '收藏'),
          ),
          TextField(
            controller: _commentsController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '评论'),
          ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: Text(_saving ? '保存中…' : '保存记录'),
          ),
        ],
      ),
    );
  }
}

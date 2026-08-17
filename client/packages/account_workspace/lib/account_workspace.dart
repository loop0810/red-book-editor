import 'package:flutter/material.dart';

class AccountWorkspacePage extends StatefulWidget {
  const AccountWorkspacePage({
    required this.accountId,
    required this.domainId,
    required this.initialPositioning,
    required this.initialTone,
    required this.initialBabyMonth,
    required this.onSave,
    super.key,
  });

  final String? accountId;
  final String domainId;
  final String initialPositioning;
  final String initialTone;
  final int initialBabyMonth;
  final Future<void> Function({
    required String? accountId,
    required String positioning,
    required String tone,
    required int currentBabyMonth,
  })
  onSave;

  @override
  State<AccountWorkspacePage> createState() => _AccountWorkspacePageState();
}

class _AccountWorkspacePageState extends State<AccountWorkspacePage> {
  late final TextEditingController _positioningController;
  late final TextEditingController _toneController;
  late int _babyMonth;
  bool _saving = false;
  String? _error;
  final _columns = <String>['科普', '经验', '软文'];

  @override
  void initState() {
    super.initState();
    _positioningController = TextEditingController(
      text: widget.initialPositioning,
    );
    _toneController = TextEditingController(text: widget.initialTone);
    _babyMonth = widget.initialBabyMonth;
  }

  @override
  void dispose() {
    _positioningController.dispose();
    _toneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('账号工作台')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _positioningController,
            decoration: const InputDecoration(labelText: '账号定位'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _toneController,
            decoration: const InputDecoration(labelText: '表达风格'),
          ),
          const SizedBox(height: 8),
          Text(
            widget.accountId == null
                ? '首次配置：当前版本无需登录，账号用于保存内容上下文'
                : '当前领域：${widget.domainId}（账号 ${widget.accountId}）',
          ),
          const SizedBox(height: 16),
          Text('当前宝宝：$_babyMonth 个月'),
          Slider(
            value: _babyMonth.toDouble(),
            min: 0,
            max: 24,
            divisions: 24,
            onChanged: (value) => setState(() => _babyMonth = value.round()),
          ),
          const SizedBox(height: 12),
          Text('内容栏目', style: Theme.of(context).textTheme.titleMedium),
          ..._columns.map(
            (column) => CheckboxListTile(
              value: true,
              onChanged: (_) {},
              title: Text(column),
            ),
          ),
          if (_error != null)
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          FilledButton(
            onPressed: _saving
                ? null
                : () async {
                    setState(() {
                      _saving = true;
                      _error = null;
                    });
                    try {
                      await widget.onSave(
                        accountId: widget.accountId,
                        positioning: _positioningController.text.trim(),
                        tone: _toneController.text.trim(),
                        currentBabyMonth: _babyMonth,
                      );
                      if (context.mounted) Navigator.of(context).pop();
                    } catch (error) {
                      if (context.mounted) {
                        setState(() => _error = '保存失败：$error');
                      }
                    } finally {
                      if (mounted) setState(() => _saving = false);
                    }
                  },
            child: Text(_saving ? '保存中…' : '保存账号配置'),
          ),
        ],
      ),
    );
  }
}

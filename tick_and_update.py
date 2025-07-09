from mcdreforged.api.all import *
import re

PLUGIN_METADATA = {
    'id': 'tick_and_update',
    'version': '1.7.0',
    'name': 'Tick and Update Controller',
    'description': '添加了!!tick指令来切换tick freeze和unfreeze以及!!update来切换carpet interactionUpdates',
    'author': 'czw06(use deepseek)',
    'link': 'https://example.com',
    'dependencies': {
        'mcdreforged': '>=2.0.0',
    }
}

# 存储状态查询请求
pending_queries = {}

def on_load(server: PluginServerInterface, old):
    server.register_help_message('!!tick', '冻结/解冻游戏刻')
    server.register_help_message('!!update', '控制交互更新优化 (true/false)')
    
    # 正确注册事件监听器
    server.register_event_listener('mcdr.general_info', on_general_info)
    server.logger.info("插件已加载，事件监听器已注册")

@new_thread(PLUGIN_METADATA['name'])
def on_info(server: PluginServerInterface, info: Info):
    if not info.is_player or info.content == '':
        return
    
    player = info.player
    permission_required = 2  # 默认OP权限等级
    
    # !!tick 命令处理
    if info.content == '!!tick':
        if server.get_permission_level(player) < permission_required:
            server.reply(info, '§c权限不足！需要权限等级 {} 或以上'.format(permission_required))
            return
        
        # 标记玩家正在等待tick状态
        pending_queries[player] = {'type': 'tick', 'command': 'tick freeze'}
        server.execute('tick freeze')
        server.reply(info, '§a正在切换游戏刻状态...')
        server.logger.info(f"玩家 {player} 执行了 !!tick")

    # !!update 命令处理
    elif info.content.startswith('!!update'):
        if server.get_permission_level(player) < permission_required:
            server.reply(info, '§c权限不足！需要权限等级 {} 或以上'.format(permission_required))
            return
        
        args = info.content.split()
        if len(args) == 1:
            # 查询状态
            pending_queries[player] = {'type': 'update_query', 'command': 'carpet interactionUpdates'}
            server.execute('carpet interactionUpdates')
            server.reply(info, '§a正在查询交互更新状态...')
            server.logger.info(f"玩家 {player} 执行了 !!update (查询)")
            
        elif len(args) == 2:
            value = args[1].lower()
            if value in ['true', 'false']:
                pending_queries[player] = {'type': 'update_set', 'value': value, 'command': f'carpet setDefault interactionUpdates {value}'}
                server.execute(f'carpet setDefault interactionUpdates {value}')
                server.reply(info, '§a正在设置交互更新状态...')
                server.logger.info(f"玩家 {player} 执行了 !!update {value}")
            else:
                server.reply(info, '§c无效参数！请使用 true 或 false')
        else:
            server.reply(info, '§e用法:\n!!update - 查询当前状态\n!!update true - 启用优化\n!!update false - 禁用优化')

def on_general_info(server: ServerInterface, info: Info):
    """处理来自服务器控制台的一般信息"""
    content = info.content
    server.logger.debug(f"收到服务器信息: {content}")
    
    # 检查是否是交互更新状态的响应
    if '当前值:' in content:
        # 提取状态值
        match = re.search(r'当前值:\s*(\w+)', content)
        if match:
            status = match.group(1).lower()
            for player, query in list(pending_queries.items()):
                if query['type'] == 'update_query':
                    server.say('§6交互更新优化当前状态: {}'.format(status))
                    server.logger.info(f"广播交互更新状态: {status}")
                    del pending_queries[player]
                    break
    
    # 检查是否是设置操作的响应
    elif '设置为' in content and 'interactionUpdates' in content:
        # 提取设置的值
        match = re.search(r'设置为\s*(\w+)', content)
        if match:
            value = match.group(1).lower()
            for player, query in list(pending_queries.items()):
                if query['type'] == 'update_set':
                    server.say('§6玩家 {} 已将交互更新优化设置为 {}'.format(player, value))
                    server.logger.info(f"广播交互更新设置: {player} -> {value}")
                    del pending_queries[player]
                    break
    
    # 检查是否是tick状态的响应
    elif 'The game is' in content:
        for player, query in list(pending_queries.items()):
            if query['type'] == 'tick':
                if 'frozen' in content:
                    server.say('§6玩家 {} 已冻结游戏刻'.format(player))
                    server.logger.info(f"广播游戏刻冻结: {player}")
                elif 'running' in content:
                    server.say('§6玩家 {} 已恢复正常游戏刻'.format(player))
                    server.logger.info(f"广播游戏刻恢复: {player}")
                del pending_queries[player]
                break

def on_unload(server: PluginServerInterface):
    """插件卸载时清理"""
    global pending_queries
    pending_queries = {}
    server.logger.info("插件已卸载")
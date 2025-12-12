"""
Утилиты для форматирования данных
"""
from datetime import datetime
from typing import Dict, Any, List
import json


def format_user_info(user: Dict[str, Any]) -> str:
    """Форматирование информации о пользователе"""
    status = "🚫 Заблокирован" if user.get('is_blocked') else "✅ Активен"
    subscription = user.get('subscription_type', 'none')
    expires = user.get('subscription_expires_at', 'N/A')
    
    text = f"""
👤 <b>Пользователь #{user.get('telegram_id')}</b>

📛 Имя: {user.get('username', 'N/A')}
📧 Email: {user.get('email', 'N/A')}
📊 Статус: {status}
💎 Подписка: {subscription}
⏰ Истекает: {format_datetime(expires)}
📅 Регистрация: {format_datetime(user.get('created_at'))}
"""
    return text


def format_strategy_info(strategy: Dict[str, Any]) -> str:
    """Форматирование информации о стратегии"""
    status = "✅ Активна" if strategy.get('is_active') else "⏸ Неактивна"
    
    text = f"""
🎯 <b>{strategy.get('name', 'Unnamed')}</b>

📝 Описание: {strategy.get('description', 'N/A')}
📊 Статус: {status}
📈 Активы: {', '.join(strategy.get('assets_to_monitor', []))}
⏰ Таймфрейм: {strategy.get('timeframe', 'N/A')}
📅 Создана: {format_datetime(strategy.get('created_at'))}
"""
    return text


def format_token_info(token: Dict[str, Any]) -> str:
    """Форматирование информации о токене"""
    status = "✅ Активен" if token.get('is_active') else "❌ Деактивирован"
    uses = f"{token.get('current_uses', 0)}/{token.get('max_uses', '∞')}"
    
    text = f"""
🎫 <code>{token.get('token')}</code>

📊 Статус: {status}
💎 Тип подписки: {token.get('subscription_type', 'trial')}
🔢 Использований: {uses}
👤 Создатель: {token.get('created_by', 'N/A')}
📅 Создан: {format_datetime(token.get('created_at'))}
"""
    return text


def format_log_entry(log: Dict[str, Any]) -> str:
    """Форматирование записи лога"""
    level = log.get('level', 'INFO')
    emoji_map = {
        'ERROR': '❌',
        'WARNING': '⚠️',
        'INFO': 'ℹ️',
        'DEBUG': '🔧'
    }
    emoji = emoji_map.get(level, 'ℹ️')
    
    text = f"{emoji} [{level}] {format_datetime(log.get('created_at'))}\n"
    text += f"📝 {log.get('message', 'N/A')}\n"
    
    if log.get('details'):
        text += f"📋 {log.get('details')}\n"
    
    return text


def format_decision_log(log: Dict[str, Any]) -> str:
    """Форматирование лога решения Ядра (reasoning log)"""
    signal_type = log.get('signal_type', 'N/A')
    asset = log.get('asset', 'N/A')
    indicators_data = log.get("indicators_data") or {}

    indicators_lines = ""
    if isinstance(indicators_data, dict) and indicators_data:
        checks = indicators_data.get("checks")
        if isinstance(checks, list) and checks:
            lines = []
            for c in checks[:20]:
                if not isinstance(c, dict):
                    continue
                ind = c.get("indicator", "N/A")
                val = c.get("current_value", "N/A")
                cond = c.get("condition", "N/A")
                res = "TRUE" if c.get("result") else "FALSE"
                bias = c.get("decision_bias", "NEUTRAL")
                lines.append(f"• {ind}: {val} -> {cond} => {res} (в пользу: {bias})")
            indicators_lines = "\n".join(lines)
        else:
            # Fallback: плоский словарь
            indicators_lines = "\n".join([f"• {k}: {v}" for k, v in indicators_data.items()])
    
    text = f"""
🧠 <b>Логика Анализа Ядра</b> - {format_datetime(log.get('created_at'))}

📊 Актив: {asset}
🎯 Сигнал: {signal_type}
📝 Обоснование:
{log.get('reasoning', 'N/A')}

{f"📌 Детали по индикаторам:\n{indicators_lines}" if indicators_lines else ""}

📈 Уверенность: {log.get('confidence', 0):.2f}%
"""
    return text


def format_statistics(stats: Dict[str, Any]) -> str:
    """Форматирование общей статистики"""
    text = f"""
📊 <b>Общая статистика системы</b>

👥 Всего пользователей: {stats.get('active_users', 0)}
📡 Всего сигналов: {stats.get('total_signals', 0)}
💹 Всего трейдов: {stats.get('total_trades', 0)}

🎯 Активная стратегия: {stats.get('active_strategy_name', 'Нет')}
⏰ Последнее обновление: {format_datetime(stats.get('last_update'))}
"""
    return text


def format_datetime(dt: Any) -> str:
    """Форматирование даты и времени"""
    if not dt:
        return "N/A"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y %H:%M")
    
    return str(dt)


def format_json(data: Dict[str, Any], max_length: int = 500) -> str:
    """Форматирование JSON для отображения"""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    if len(json_str) > max_length:
        json_str = json_str[:max_length] + "\n..."
    
    return f"<pre>{json_str}</pre>"


def paginate_list(items: List[Any], page: int = 1, per_page: int = 10) -> tuple[List[Any], int]:
    """Пагинация списка"""
    start = (page - 1) * per_page
    end = start + per_page
    total_pages = (len(items) + per_page - 1) // per_page
    
    return items[start:end], total_pages


def escape_html(text: str) -> str:
    """Экранирование HTML символов"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

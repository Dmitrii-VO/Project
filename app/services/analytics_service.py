# app/services/analytics_service.py
"""
Сервис аналитики для Telegram Mini App
Объединяет всю статистику из моделей и предоставляет единый интерфейс для дашборда
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import statistics

from ..models.user import User, UserAnalytics
from ..models.channels import Channel, ChannelStatistics
from ..models.offer import Offer, OfferAnalytics
from ..models.payment import Payment
from ..models.database import db_manager
from ..utils.exceptions import AnalyticsError
from ..config.settings import PLATFORM_COMMISSION_PERCENT


class AnalyticsService:
    """Основной сервис аналитики"""

    @staticmethod
    def get_date_range(period: str = '30d') -> Tuple[datetime, datetime]:
        """Получение диапазона дат для анализа"""
        end_date = datetime.now()

        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        elif period == 'all':
            start_date = datetime(2020, 1, 1)  # Начало времен
        else:
            # Пытаемся распарсить кастомный период
            try:
                days = int(period.rstrip('d'))
                start_date = end_date - timedelta(days=days)
            except (ValueError, AttributeError):
                start_date = end_date - timedelta(days=30)

        return start_date, end_date

    @staticmethod
    def calculate_growth_rate(current: float, previous: float) -> float:
        """Расчет темпа роста в процентах"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0

        return round(((current - previous) / previous) * 100, 2)

    @staticmethod
    def get_platform_overview() -> Dict[str, Any]:
        """Получение общего обзора платформы"""
        try:
            # Статистика пользователей
            user_stats = UserAnalytics.get_platform_user_stats()

            # Статистика каналов
            channel_stats = ChannelStatistics.get_platform_stats()

            # Статистика офферов
            offer_stats = OfferAnalytics.get_platform_offer_stats()

            # Финансовая статистика
            financial_stats = AnalyticsService._get_platform_financial_stats()

            return {
                'users': user_stats,
                'channels': channel_stats,
                'offers': offer_stats,
                'finance': financial_stats,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            raise AnalyticsError(f"Ошибка получения обзора платформы: {str(e)}")

    @staticmethod
    def _get_platform_financial_stats() -> Dict[str, Any]:
        """Получение финансовой статистики платформы"""
        try:
            # Общий оборот
            total_volume = db_manager.execute_query(
                """
                SELECT SUM(ABS(amount))
                FROM payments
                WHERE status = 'completed'
                  AND payment_type IN ('deposit', 'withdrawal', 'escrow_release')
                """,
                fetch_one=True
            )[0] or 0

            # Активные балансы
            total_balance = db_manager.execute_query(
                "SELECT SUM(balance) FROM users",
                fetch_one=True
            )[0] or 0

            # Доходы платформы (комиссии)
            platform_revenue = db_manager.execute_query(
                """
                SELECT SUM(commission_amount)
                FROM payments
                WHERE status = 'completed'
                  AND commission_amount > 0
                """,
                fetch_one=True
            )[0] or 0

            # Статистика по дням за последний месяц
            daily_volume = db_manager.execute_query(
                """
                SELECT DATE (created_at) as date, SUM (ABS(amount)) as volume
                FROM payments
                WHERE status = 'completed'
                  AND created_at >= datetime('now'
                    , '-30 days')
                GROUP BY DATE (created_at)
                ORDER BY date DESC
                """,
                fetch_all=True
            )

            return {
                'total_volume': float(total_volume),
                'total_balance': float(total_balance),
                'platform_revenue': float(platform_revenue),
                'commission_rate': PLATFORM_COMMISSION_PERCENT,
                'daily_volume': [
                    {'date': row[0], 'volume': float(row[1])}
                    for row in daily_volume
                ] if daily_volume else []
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def get_user_dashboard(user_id: int, period: str = '30d') -> Dict[str, Any]:
        """Получение персонального дашборда пользователя"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise AnalyticsError("Пользователь не найден")

            start_date, end_date = AnalyticsService.get_date_range(period)

            dashboard = {
                'user_info': {
                    'id': user.id,
                    'username': user.username,
                    'user_type': user.user_type,
                    'status': user.status,
                    'created_at': user.created_at
                },
                'period': {
                    'range': period,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'generated_at': datetime.now().isoformat()
            }

            # Основные метрики
            dashboard['main_metrics'] = AnalyticsService._get_user_main_metrics(user, start_date, end_date)

            # Финансовые данные
            dashboard['financial_data'] = AnalyticsService._get_user_financial_data(user, start_date, end_date)

            # Данные для графиков
            dashboard['charts'] = AnalyticsService._get_user_chart_data(user, start_date, end_date)

            # Производительность
            dashboard['performance'] = AnalyticsService._get_user_performance_data(user, start_date, end_date)

            # Рекомендации
            dashboard['recommendations'] = AnalyticsService._get_user_recommendations(user)

            # Достижения
            dashboard['achievements'] = AnalyticsService._get_user_achievements_summary(user)

            return dashboard

        except Exception as e:
            raise AnalyticsError(f"Ошибка получения дашборда пользователя: {str(e)}")

    @staticmethod
    def _get_user_main_metrics(user: User, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение основных метрик пользователя"""
        try:
            metrics = {
                'balance': float(user.balance),
                'total_earned': float(user.total_earned),
                'total_spent': float(user.total_spent),
                'profit': float(user.total_earned - user.total_spent)
            }

            # Метрики для владельцев каналов
            if user.user_type in ['channel_owner', 'both']:
                channel_metrics = AnalyticsService._get_channel_owner_metrics(user.id, start_date, end_date)
                metrics.update(channel_metrics)

            # Метрики для рекламодателей
            if user.user_type in ['advertiser', 'both']:
                advertiser_metrics = AnalyticsService._get_advertiser_metrics(user.id, start_date, end_date)
                metrics.update(advertiser_metrics)

            return metrics

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_channel_owner_metrics(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Метрики для владельца каналов"""
        try:
            # Количество каналов
            total_channels = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_active = 1",
                (user_id,),
                fetch_one=True
            )[0]

            verified_channels = db_manager.execute_query(
                "SELECT COUNT(*) FROM channels WHERE owner_id = ? AND is_verified = 1",
                (user_id,),
                fetch_one=True
            )[0]

            # Общее количество подписчиков
            total_subscribers = db_manager.execute_query(
                "SELECT SUM(subscribers_count) FROM channels WHERE owner_id = ? AND is_active = 1",
                (user_id,),
                fetch_one=True
            )[0] or 0

            # Отклики за период
            period_responses = db_manager.execute_query(
                """
                SELECT COUNT(*)                                               as total,
                       SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END)   as accepted,
                       SUM(CASE WHEN status = 'posted' THEN price ELSE 0 END) as earnings
                FROM offer_responses or1
                         JOIN channels c ON or1.channel_id = c.id
                WHERE c.owner_id = ?
                  AND or1.created_at >= ?
                  AND or1.created_at <= ?
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_one=True
            )

            return {
                'channels': {
                    'total': total_channels,
                    'verified': verified_channels,
                    'verification_rate': (verified_channels / total_channels * 100) if total_channels > 0 else 0,
                    'total_subscribers': int(total_subscribers)
                },
                'responses': {
                    'total': period_responses[0],
                    'accepted': period_responses[1],
                    'acceptance_rate': (period_responses[1] / period_responses[0] * 100) if period_responses[
                                                                                                0] > 0 else 0,
                    'period_earnings': float(period_responses[2] or 0)
                }
            }

        except Exception as e:
            return {'channels': {}, 'responses': {}, 'error': str(e)}

    @staticmethod
    def _get_advertiser_metrics(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Метрики для рекламодателя"""
        try:
            # Статистика офферов
            offers_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                              as total,
                       SUM(budget)                                           as total_budget,
                       SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)    as active,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM offers
                WHERE advertiser_id = ?
                  AND created_at >= ?
                  AND created_at <= ?
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_one=True
            )

            # Статистика откликов
            responses_stats = db_manager.execute_query(
                """
                SELECT COUNT(*)                                                 as total_responses,
                       SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted,
                       AVG(or1.price)                                           as avg_price,
                       SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END)   as posted
                FROM offer_responses or1
                         JOIN offers o ON or1.offer_id = o.id
                WHERE o.advertiser_id = ?
                  AND or1.created_at >= ?
                  AND or1.created_at <= ?
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_one=True
            )

            return {
                'offers': {
                    'total': offers_stats[0],
                    'active': offers_stats[2],
                    'completed': offers_stats[3],
                    'completion_rate': (offers_stats[3] / offers_stats[0] * 100) if offers_stats[0] > 0 else 0,
                    'total_budget': float(offers_stats[1] or 0)
                },
                'campaigns': {
                    'responses_received': responses_stats[0],
                    'responses_accepted': responses_stats[1],
                    'avg_response_price': round(float(responses_stats[2] or 0), 2),
                    'posts_published': responses_stats[3],
                    'success_rate': (responses_stats[3] / responses_stats[0] * 100) if responses_stats[0] > 0 else 0
                }
            }

        except Exception as e:
            return {'offers': {}, 'campaigns': {}, 'error': str(e)}

    @staticmethod
    def _get_user_financial_data(user: User, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение финансовых данных пользователя"""
        try:
            # История платежей за период
            payments_data = db_manager.execute_query(
                """
                SELECT payment_type,
                       SUM(amount) as total_amount,
                       COUNT(*) as count
                FROM payments
                WHERE user_id = ?
                  AND status = 'completed'
                  AND created_at >= ?
                  AND created_at <= ?
                GROUP BY payment_type
                """,
                (user.id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            # Разбиваем по типам
            income = 0
            expenses = 0
            for payment_type, amount, count in payments_data:
                if amount > 0:
                    income += amount
                else:
                    expenses += abs(amount)

            # Ежедневная динамика за период
            daily_finance = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, SUM (CASE WHEN amount > 0 THEN amount ELSE 0 END) as income, SUM (CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                FROM payments
                WHERE user_id = ?
                  AND status = 'completed'
                  AND created_at >= ?
                  AND created_at <= ?
                GROUP BY DATE (created_at)
                ORDER BY date
                """,
                (user.id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            return {
                'period_summary': {
                    'income': float(income),
                    'expenses': float(expenses),
                    'net_result': float(income - expenses)
                },
                'payment_types': [
                    {
                        'type': payment_type,
                        'amount': float(amount),
                        'count': count
                    }
                    for payment_type, amount, count in payments_data
                ],
                'daily_timeline': [
                    {
                        'date': date,
                        'income': float(income),
                        'expenses': float(expenses),
                        'net': float(income - expenses)
                    }
                    for date, income, expenses in daily_finance
                ]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_user_chart_data(user: User, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение данных для графиков пользователя"""
        try:
            charts = {}

            # График доходов по дням
            revenue_chart = AnalyticsService._generate_revenue_chart(user.id, start_date, end_date)
            charts['revenue'] = revenue_chart

            # График активности
            activity_chart = AnalyticsService._generate_activity_chart(user.id, start_date, end_date)
            charts['activity'] = activity_chart

            # Для владельцев каналов - распределение по каналам
            if user.user_type in ['channel_owner', 'both']:
                channels_chart = AnalyticsService._generate_channels_distribution_chart(user.id)
                charts['channels'] = channels_chart

            # Для рекламодателей - эффективность кампаний
            if user.user_type in ['advertiser', 'both']:
                campaigns_chart = AnalyticsService._generate_campaigns_performance_chart(user.id, start_date, end_date)
                charts['campaigns'] = campaigns_chart

            return charts

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _generate_revenue_chart(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Генерация графика доходов"""
        try:
            # Получаем данные по дням
            daily_revenue = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, SUM (CASE WHEN amount > 0 THEN amount ELSE 0 END) as income, SUM (CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses
                FROM payments
                WHERE user_id = ?
                  AND status = 'completed'
                  AND created_at >= ?
                  AND created_at <= ?
                GROUP BY DATE (created_at)
                ORDER BY date
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            # Заполняем пропуски нулями
            labels = []
            income_data = []
            expenses_data = []

            current_date = start_date.date()
            end_date_obj = end_date.date()

            revenue_dict = {row[0]: (row[1], row[2]) for row in daily_revenue}

            while current_date <= end_date_obj:
                date_str = current_date.isoformat()
                labels.append(current_date.strftime('%d.%m'))

                if date_str in revenue_dict:
                    income_data.append(float(revenue_dict[date_str][0]))
                    expenses_data.append(float(revenue_dict[date_str][1]))
                else:
                    income_data.append(0)
                    expenses_data.append(0)

                current_date += timedelta(days=1)

            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Доходы',
                        'data': income_data,
                        'borderColor': '#10B981',
                        'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                        'fill': True
                    },
                    {
                        'label': 'Расходы',
                        'data': expenses_data,
                        'borderColor': '#EF4444',
                        'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                        'fill': True
                    }
                ]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _generate_activity_chart(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Генерация графика активности"""
        try:
            # Активность по дням (офферы, отклики, транзакции)
            activity_data = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, COUNT (*) as activity_count
                FROM (
                    SELECT created_at FROM offers WHERE advertiser_id = ?
                    UNION ALL
                    SELECT or1.created_at FROM offer_responses or1
                    JOIN channels c ON or1.channel_id = c.id WHERE c.owner_id = ?
                    UNION ALL
                    SELECT created_at FROM payments WHERE user_id = ?
                    ) combined_activity
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY DATE (created_at)
                ORDER BY date
                """,
                (user_id, user_id, user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            # Подготавливаем данные
            labels = []
            data = []

            current_date = start_date.date()
            end_date_obj = end_date.date()

            activity_dict = {row[0]: row[1] for row in activity_data}

            while current_date <= end_date_obj:
                date_str = current_date.isoformat()
                labels.append(current_date.strftime('%d.%m'))
                data.append(activity_dict.get(date_str, 0))
                current_date += timedelta(days=1)

            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Активность',
                    'data': data,
                    'borderColor': '#3B82F6',
                    'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                    'fill': True
                }]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _generate_channels_distribution_chart(user_id: int) -> Dict[str, Any]:
        """Генерация графика распределения каналов"""
        try:
            channels_data = db_manager.execute_query(
                """
                SELECT channel_name,
                       subscribers_count,
                       (SELECT COUNT(*)
                        FROM offer_responses or1
                        WHERE or1.channel_id = c.id
                          AND or1.status = 'posted') as posts_count
                FROM channels c
                WHERE owner_id = ?
                  AND is_active = 1
                ORDER BY subscribers_count DESC LIMIT 10
                """,
                (user_id,),
                fetch_all=True
            )

            labels = [row[0] for row in channels_data]
            subscribers_data = [row[1] for row in channels_data]
            posts_data = [row[2] for row in channels_data]

            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Подписчики',
                        'data': subscribers_data,
                        'backgroundColor': [
                            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6B7280'
                        ]
                    }
                ]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _generate_campaigns_performance_chart(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Генерация графика эффективности кампаний"""
        try:
            campaigns_data = db_manager.execute_query(
                """
                SELECT o.title,
                       o.budget,
                       COUNT(or1.id)                                          as responses_count,
                       SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END) as posted_count
                FROM offers o
                         LEFT JOIN offer_responses or1 ON o.id = or1.offer_id
                WHERE o.advertiser_id = ?
                  AND o.created_at >= ?
                  AND o.created_at <= ?
                GROUP BY o.id, o.title, o.budget
                ORDER BY posted_count DESC LIMIT 10
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            labels = [row[0][:20] + '...' if len(row[0]) > 20 else row[0] for row in campaigns_data]
            budget_data = [float(row[1]) for row in campaigns_data]
            efficiency_data = [(row[3] / row[2] * 100) if row[2] > 0 else 0 for row in campaigns_data]

            return {
                'labels': labels,
                'datasets': [
                    {
                        'label': 'Бюджет (₽)',
                        'data': budget_data,
                        'backgroundColor': 'rgba(59, 130, 246, 0.8)',
                        'yAxisID': 'budget'
                    },
                    {
                        'label': 'Эффективность (%)',
                        'data': efficiency_data,
                        'backgroundColor': 'rgba(16, 185, 129, 0.8)',
                        'yAxisID': 'efficiency'
                    }
                ]
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_user_performance_data(user: User, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Получение данных о производительности пользователя"""
        try:
            performance = {}

            if user.user_type in ['channel_owner', 'both']:
                # Производительность каналов
                channels_performance = db_manager.execute_query(
                    """
                    SELECT c.id,
                           c.channel_name,
                           c.subscribers_count,
                           c.price_per_post,
                           COUNT(or1.id)                                                  as total_responses,
                           SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END)       as accepted_responses,
                           SUM(CASE WHEN or1.status = 'posted' THEN or1.price ELSE 0 END) as earnings,
                           c.is_verified
                    FROM channels c
                             LEFT JOIN offer_responses or1 ON c.id = or1.channel_id
                        AND or1.created_at >= ? AND or1.created_at <= ?
                    WHERE c.owner_id = ?
                      AND c.is_active = 1
                    GROUP BY c.id
                    ORDER BY earnings DESC
                    """,
                    (start_date.isoformat(), end_date.isoformat(), user.id),
                    fetch_all=True
                )

                performance['channels'] = [
                    {
                        'id': row[0],
                        'name': row[1],
                        'subscribers': row[2],
                        'price_per_post': float(row[3]),
                        'total_responses': row[4],
                        'accepted_responses': row[5],
                        'acceptance_rate': (row[5] / row[4] * 100) if row[4] > 0 else 0,
                        'earnings': float(row[6] or 0),
                        'cpm': (float(row[3]) / row[2] * 1000) if row[2] > 0 else 0,
                        'is_verified': bool(row[7])
                    }
                    for row in channels_performance
                ]

            if user.user_type in ['advertiser', 'both']:
                # Производительность кампаний
                campaigns_performance = db_manager.execute_query(
                    """
                    SELECT o.id,
                           o.title,
                           o.category,
                           o.budget,
                           COUNT(or1.id)                                            as total_responses,
                           SUM(CASE WHEN or1.status = 'accepted' THEN 1 ELSE 0 END) as accepted_responses,
                           SUM(CASE WHEN or1.status = 'posted' THEN 1 ELSE 0 END)   as posted_responses,
                           AVG(or1.price)                                           as avg_response_price,
                           o.status
                    FROM offers o
                             LEFT JOIN offer_responses or1 ON o.id = or1.offer_id
                        AND or1.created_at >= ? AND or1.created_at <= ?
                    WHERE o.advertiser_id = ?
                    GROUP BY o.id
                    ORDER BY posted_responses DESC
                    """,
                    (start_date.isoformat(), end_date.isoformat(), user.id),
                    fetch_all=True
                )

                performance['campaigns'] = [
                    {
                        'id': row[0],
                        'title': row[1],
                        'category': row[2],
                        'budget': float(row[3]),
                        'total_responses': row[4],
                        'accepted_responses': row[5],
                        'posted_responses': row[6],
                        'response_rate': (row[4] / 1 * 100) if row[4] > 0 else 0,  # Можно улучшить
                        'success_rate': (row[6] / row[4] * 100) if row[4] > 0 else 0,
                        'avg_response_price': round(float(row[7] or 0), 2),
                        'efficiency_score': AnalyticsService._calculate_campaign_efficiency(row),
                        'status': row[8]
                    }
                    for row in campaigns_performance
                ]

            return performance

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _calculate_campaign_efficiency(campaign_row) -> float:
        """Расчет эффективности кампании"""
        try:
            budget = float(campaign_row[3])
            total_responses = campaign_row[4]
            posted_responses = campaign_row[6]
            avg_price = float(campaign_row[7] or 0)

            if budget == 0 or total_responses == 0:
                return 0

            # Формула эффективности: (успешные размещения / общие отклики) * (средняя цена / бюджет) * 100
            success_rate = posted_responses / total_responses
            cost_efficiency = avg_price / budget if budget > 0 else 0

            efficiency = success_rate * cost_efficiency * 100
            return round(min(efficiency, 100), 1)  # Максимум 100%

        except (ValueError, ZeroDivisionError, TypeError):
            return 0

    @staticmethod
    def _get_user_recommendations(user: User) -> List[Dict[str, Any]]:
        """Получение рекомендаций для пользователя"""
        try:
            from ..models.user import UserRecommendationService
            return UserRecommendationService.get_personalized_recommendations(user)

        except Exception as e:
            return [{'type': 'error', 'title': 'Ошибка рекомендаций', 'description': str(e)}]

    @staticmethod
    def _get_user_achievements_summary(user: User) -> Dict[str, Any]:
        """Получение краткой сводки достижений пользователя"""
        try:
            from ..models.user import UserUtils

            # Получаем рейтинг
            rating = UserUtils.calculate_user_rating(user)

            # Получаем достижения
            achievements = UserUtils.get_user_achievements(user)

            # Группируем по категориям
            achievements_by_category = defaultdict(list)
            for achievement in achievements:
                achievements_by_category[achievement.get('category', 'разное')].append(achievement)

            return {
                'rating': rating,
                'total_achievements': len(achievements),
                'achievements_by_category': dict(achievements_by_category),
                'recent_achievements': achievements[-3:] if achievements else []  # Последние 3
            }

        except Exception as e:
            return {'error': str(e)}


class AdvancedAnalyticsService:
    """Расширенный сервис аналитики с AI и прогнозированием"""

    @staticmethod
    def get_predictive_analytics(user_id: int, horizon_days: int = 30) -> Dict[str, Any]:
        """Получение прогнозной аналитики"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {'error': 'User not found'}

            # Анализируем исторические данные за последние 90 дней
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)

            # Получаем исторические данные
            historical_data = AdvancedAnalyticsService._get_historical_performance(user_id, start_date, end_date)

            # Генерируем прогноз
            predictions = AdvancedAnalyticsService._generate_predictions(historical_data, horizon_days)

            # Анализируем тренды
            trends = AdvancedAnalyticsService._analyze_trends(historical_data)

            return {
                'user_id': user_id,
                'prediction_horizon_days': horizon_days,
                'historical_period_days': 90,
                'predictions': predictions,
                'trends': trends,
                'confidence_level': AdvancedAnalyticsService._calculate_confidence_level(historical_data),
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_historical_performance(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, List]:
        """Получение исторических данных о производительности"""
        try:
            # Ежедневные доходы
            daily_revenue = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, SUM (CASE WHEN amount > 0 THEN amount ELSE 0 END) as revenue
                FROM payments
                WHERE user_id = ?
                  AND status = 'completed'
                  AND created_at >= ?
                  AND created_at <= ?
                GROUP BY DATE (created_at)
                ORDER BY date
                """,
                (user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            # Ежедневная активность
            daily_activity = db_manager.execute_query(
                """
                SELECT
                    DATE (created_at) as date, COUNT (*) as activity_count
                FROM (
                    SELECT created_at FROM offers WHERE advertiser_id = ?
                    UNION ALL
                    SELECT or1.created_at FROM offer_responses or1
                    JOIN channels c ON or1.channel_id = c.id WHERE c.owner_id = ?
                    ) combined_activity
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY DATE (created_at)
                ORDER BY date
                """,
                (user_id, user_id, start_date.isoformat(), end_date.isoformat()),
                fetch_all=True
            )

            return {
                'revenue': [{'date': row[0], 'value': float(row[1])} for row in daily_revenue],
                'activity': [{'date': row[0], 'value': row[1]} for row in daily_activity]
            }

        except Exception as e:
            return {'revenue': [], 'activity': [], 'error': str(e)}

    @staticmethod
    def _generate_predictions(historical_data: Dict[str, List], horizon_days: int) -> Dict[str, Any]:
        """Генерация прогнозов на основе исторических данных"""
        try:
            predictions = {}

            # Прогноз доходов
            revenue_data = [item['value'] for item in historical_data.get('revenue', [])]
            if len(revenue_data) >= 7:  # Минимум неделя данных
                revenue_prediction = AdvancedAnalyticsService._simple_linear_forecast(revenue_data, horizon_days)
                predictions['revenue'] = {
                    'forecast': revenue_prediction,
                    'trend': 'up' if revenue_prediction[-1] > revenue_prediction[0] else 'down',
                    'total_predicted': sum(revenue_prediction),
                    'daily_average': statistics.mean(revenue_prediction) if revenue_prediction else 0
                }

            # Прогноз активности
            activity_data = [item['value'] for item in historical_data.get('activity', [])]
            if len(activity_data) >= 7:
                activity_prediction = AdvancedAnalyticsService._simple_linear_forecast(activity_data, horizon_days)
                predictions['activity'] = {
                    'forecast': activity_prediction,
                    'trend': 'up' if activity_prediction[-1] > activity_prediction[0] else 'down',
                    'total_predicted': sum(activity_prediction),
                    'daily_average': statistics.mean(activity_prediction) if activity_prediction else 0
                }

            return predictions

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _simple_linear_forecast(data: List[float], forecast_days: int) -> List[float]:
        """Простое линейное прогнозирование"""
        try:
            if len(data) < 2:
                return [0] * forecast_days

            # Вычисляем тренд (простая линейная регрессия)
            n = len(data)
            x = list(range(n))

            # Средние значения
            x_mean = statistics.mean(x)
            y_mean = statistics.mean(data)

            # Вычисляем коэффициенты
            numerator = sum((x[i] - x_mean) * (data[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                return [y_mean] * forecast_days

            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

            # Генерируем прогноз
            forecast = []
            for i in range(forecast_days):
                future_x = n + i
                predicted_value = slope * future_x + intercept
                # Не даем прогнозу уйти в отрицательные значения
                forecast.append(max(0, predicted_value))

            return forecast

        except Exception as e:
            return [0] * forecast_days

    @staticmethod
    def _analyze_trends(historical_data: Dict[str, List]) -> Dict[str, Any]:
        """Анализ трендов в исторических данных"""
        try:
            trends = {}

            # Анализ тренда доходов
            revenue_data = [item['value'] for item in historical_data.get('revenue', [])]
            if len(revenue_data) >= 14:  # Минимум 2 недели данных
                first_week = statistics.mean(revenue_data[:7])
                last_week = statistics.mean(revenue_data[-7:])

                revenue_change = ((last_week - first_week) / first_week * 100) if first_week > 0 else 0

                trends['revenue'] = {
                    'direction': 'up' if revenue_change > 5 else 'down' if revenue_change < -5 else 'stable',
                    'change_percent': round(revenue_change, 2),
                    'volatility': AdvancedAnalyticsService._calculate_volatility(revenue_data),
                    'best_day_avg': max(revenue_data) if revenue_data else 0,
                    'worst_day_avg': min(revenue_data) if revenue_data else 0
                }

            # Анализ тренда активности
            activity_data = [item['value'] for item in historical_data.get('activity', [])]
            if len(activity_data) >= 14:
                first_week_activity = statistics.mean(activity_data[:7])
                last_week_activity = statistics.mean(activity_data[-7:])

                activity_change = ((
                                               last_week_activity - first_week_activity) / first_week_activity * 100) if first_week_activity > 0 else 0

                trends['activity'] = {
                    'direction': 'up' if activity_change > 10 else 'down' if activity_change < -10 else 'stable',
                    'change_percent': round(activity_change, 2),
                    'volatility': AdvancedAnalyticsService._calculate_volatility(activity_data),
                    'peak_activity': max(activity_data) if activity_data else 0,
                    'avg_activity': statistics.mean(activity_data) if activity_data else 0
                }

            return trends

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _calculate_volatility(data: List[float]) -> float:
        """Расчет волатильности данных"""
        try:
            if len(data) < 2:
                return 0

            mean_val = statistics.mean(data)
            variance = sum((x - mean_val) ** 2 for x in data) / len(data)
            volatility = (variance ** 0.5) / mean_val * 100 if mean_val > 0 else 0

            return round(volatility, 2)

        except Exception:
            return 0

    @staticmethod
    def _calculate_confidence_level(historical_data: Dict[str, List]) -> Dict[str, float]:
        """Расчет уровня уверенности в прогнозах"""
        try:
            revenue_data = historical_data.get('revenue', [])
            activity_data = historical_data.get('activity', [])

            # Уверенность зависит от количества данных и их стабильности
            revenue_confidence = 0
            activity_confidence = 0

            if len(revenue_data) >= 30:  # Месяц данных
                revenue_values = [item['value'] for item in revenue_data if isinstance(item, dict)]
                if revenue_values:
                    volatility = AdvancedAnalyticsService._calculate_volatility(revenue_values)
                    # Чем меньше волатильность, тем выше уверенность
                    revenue_confidence = max(0, min(100, 100 - volatility))

            if len(activity_data) >= 30:
                activity_values = [item['value'] for item in activity_data if isinstance(item, dict)]
                if activity_values:
                    volatility = AdvancedAnalyticsService._calculate_volatility(activity_values)
                    activity_confidence = max(0, min(100, 100 - volatility))

            return {
                'revenue_confidence': round(revenue_confidence, 1),
                'activity_confidence': round(activity_confidence, 1),
                'overall_confidence': round((revenue_confidence + activity_confidence) / 2, 1)
            }

        except Exception as e:
            return {'revenue_confidence': 0, 'activity_confidence': 0, 'overall_confidence': 0}


class RealtimeAnalyticsService:
    """Сервис аналитики в реальном времени"""

    @staticmethod
    def get_live_metrics(user_id: int) -> Dict[str, Any]:
        """Получение метрик в реальном времени"""
        try:
            current_time = datetime.now()
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

            # Метрики за сегодня
            today_metrics = RealtimeAnalyticsService._get_today_metrics(user_id, today_start, current_time)

            # Метрики за последний час
            hour_ago = current_time - timedelta(hours=1)
            hourly_metrics = RealtimeAnalyticsService._get_hourly_metrics(user_id, hour_ago, current_time)

            # Активные процессы
            active_processes = RealtimeAnalyticsService._get_active_processes(user_id)

            return {
                'timestamp': current_time.isoformat(),
                'today': today_metrics,
                'last_hour': hourly_metrics,
                'active_processes': active_processes,
                'system_status': RealtimeAnalyticsService._get_system_status()
            }

        except Exception as e:
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    @staticmethod
    def _get_today_metrics(user_id: int, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Метрики за сегодня"""
        try:
            # Доходы сегодня
            today_revenue = db_manager.execute_query(
                """
                SELECT SUM(amount)
                FROM payments
                WHERE user_id = ?
                  AND status = 'completed'
                  AND amount > 0
                  AND created_at >= ?
                  AND created_at <= ?
                """,
                (user_id, start_time.isoformat(), end_time.isoformat()),
                fetch_one=True
            )[0] or 0

            # Новые отклики сегодня
            today_responses = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM offer_responses or1
                         JOIN channels c ON or1.channel_id = c.id
                WHERE c.owner_id = ?
                  AND or1.created_at >= ?
                  AND or1.created_at <= ?
                """,
                (user_id, start_time.isoformat(), end_time.isoformat()),
                fetch_one=True
            )[0]

            # Новые офферы сегодня
            today_offers = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM offers
                WHERE advertiser_id = ?
                  AND created_at >= ?
                  AND created_at <= ?
                """,
                (user_id, start_time.isoformat(), end_time.isoformat()),
                fetch_one=True
            )[0]

            return {
                'revenue': float(today_revenue),
                'new_responses': today_responses,
                'new_offers': today_offers,
                'period': 'today'
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_hourly_metrics(user_id: int, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Метрики за последний час"""
        try:
            # Активность за час
            hourly_activity = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM (SELECT created_at
                      FROM offers
                      WHERE advertiser_id = ?
                      UNION ALL
                      SELECT or1.created_at
                      FROM offer_responses or1
                               JOIN channels c ON or1.channel_id = c.id
                      WHERE c.owner_id = ?
                      UNION ALL
                      SELECT created_at
                      FROM payments
                      WHERE user_id = ?) combined_activity
                WHERE created_at >= ?
                  AND created_at <= ?
                """,
                (user_id, user_id, user_id, start_time.isoformat(), end_time.isoformat()),
                fetch_one=True
            )[0]

            return {
                'activity_events': hourly_activity,
                'period': 'last_hour'
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_active_processes(user_id: int) -> Dict[str, Any]:
        """Получение активных процессов пользователя"""
        try:
            # Активные офферы
            active_offers = db_manager.execute_query(
                "SELECT COUNT(*) FROM offers WHERE advertiser_id = ? AND status = 'active'",
                (user_id,),
                fetch_one=True
            )[0]

            # Ожидающие отклики
            pending_responses = db_manager.execute_query(
                """
                SELECT COUNT(*)
                FROM offer_responses or1
                         JOIN channels c ON or1.channel_id = c.id
                WHERE c.owner_id = ?
                  AND or1.status = 'pending'
                """,
                (user_id,),
                fetch_one=True
            )[0]

            # Ожидающие платежи
            pending_payments = db_manager.execute_query(
                "SELECT COUNT(*) FROM payments WHERE user_id = ? AND status = 'pending'",
                (user_id,),
                fetch_one=True
            )[0]

            return {
                'active_offers': active_offers,
                'pending_responses': pending_responses,
                'pending_payments': pending_payments
            }

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_system_status() -> Dict[str, Any]:
        """Получение статуса системы"""
        try:
            # Проверяем доступность базы данных
            db_status = 'ok'
            try:
                db_manager.execute_query("SELECT 1", fetch_one=True)
            except Exception:
                db_status = 'error'

            return {
                'database': db_status,
                'analytics': 'ok',
                'api': 'ok'
            }

        except Exception as e:
            return {'error': str(e)}


class ExportService:
    """Сервис экспорта аналитических данных"""

    @staticmethod
    def export_user_report(user_id: int, period: str = '30d', format: str = 'json') -> Dict[str, Any]:
        """Экспорт отчета пользователя"""
        try:
            # Получаем полные данные пользователя
            dashboard_data = AnalyticsService.get_user_dashboard(user_id, period)

            if format == 'json':
                return {
                    'export_format': 'json',
                    'generated_at': datetime.now().isoformat(),
                    'data': dashboard_data
                }
            elif format == 'csv':
                # Преобразуем в CSV-совместимый формат
                csv_data = ExportService._convert_to_csv_format(dashboard_data)
                return {
                    'export_format': 'csv',
                    'generated_at': datetime.now().isoformat(),
                    'csv_data': csv_data
                }
            else:
                return {'error': 'Unsupported export format'}

        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _convert_to_csv_format(dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Преобразование данных дашборда в CSV формат"""
        try:
            csv_rows = []

            # Основные метрики
            if 'main_metrics' in dashboard_data:
                metrics = dashboard_data['main_metrics']
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        csv_rows.append({
                            'category': 'main_metrics',
                            'metric': key,
                            'value': value,
                            'date': datetime.now().date().isoformat()
                        })

            # Финансовые данные по дням
            if 'financial_data' in dashboard_data and 'daily_timeline' in dashboard_data['financial_data']:
                for day_data in dashboard_data['financial_data']['daily_timeline']:
                    csv_rows.append({
                        'category': 'daily_finance',
                        'metric': 'income',
                        'value': day_data['income'],
                        'date': day_data['date']
                    })
                    csv_rows.append({
                        'category': 'daily_finance',
                        'metric': 'expenses',
                        'value': day_data['expenses'],
                        'date': day_data['date']
                    })

            return csv_rows

        except Exception as e:
            return [{'error': str(e)}]

    @staticmethod
    def generate_analytics_summary(user_id: int, period: str = '30d') -> Dict[str, Any]:
        """Генерация краткой сводки аналитики"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {'error': 'User not found'}

            start_date, end_date = AnalyticsService.get_date_range(period)

            # Собираем ключевые показатели
            summary = {
                'user_info': {
                    'username': user.username or f"User_{user.id}",
                    'user_type': user.user_type,
                    'member_since': user.created_at
                },
                'period': {
                    'range': period,
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }

            # Основные достижения
            key_metrics = AnalyticsService._get_user_main_metrics(user, start_date, end_date)

            highlights = []

            # Добавляем хайлайты на основе данных
            if key_metrics.get('balance', 0) > 10000:
                highlights.append(f"💰 Баланс: {key_metrics['balance']:,.0f} ₽")

            if user.user_type in ['channel_owner', 'both'] and 'channels' in key_metrics:
                channel_data = key_metrics['channels']
                if channel_data['total'] > 0:
                    highlights.append(
                        f"📺 Каналов: {channel_data['total']} ({channel_data['verified']} верифицированных)")
                    highlights.append(f"👥 Общая аудитория: {channel_data['total_subscribers']:,}")

            if user.user_type in ['advertiser', 'both'] and 'offers' in key_metrics:
                offer_data = key_metrics['offers']
                if offer_data['total'] > 0:
                    highlights.append(f"🎯 Кампаний: {offer_data['total']} (завершено: {offer_data['completed']})")
                    highlights.append(f"💸 Общий бюджет: {offer_data['total_budget']:,.0f} ₽")

            summary['highlights'] = highlights
            summary['key_metrics'] = key_metrics

            return summary

        except Exception as e:
            return {'error': str(e)}


# Инициализация сервисов аналитики
def initialize_analytics_services():
    """Инициализация всех сервисов аналитики"""
    try:
        # Проверяем подключение к базе данных
        db_manager.execute_query("SELECT 1", fetch_one=True)

        return {
            'analytics_service': True,
            'advanced_analytics': True,
            'realtime_analytics': True,
            'export_service': True,
            'status': 'initialized'
        }

    except Exception as e:
        return {
            'analytics_service': False,
            'advanced_analytics': False,
            'realtime_analytics': False,
            'export_service': False,
            'status': 'error',
            'error': str(e)
        }
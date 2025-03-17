import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import json
from io import StringIO
import calendar
from datetime import timedelta

# Настройка страницы
st.set_page_config(page_title="Трекер тренировок", layout="wide")

# Определение тренировок и упражнений
WORKOUTS = {
    "Тренировка A": ["Жим лежа", "Приседания", "Тяга в наклоне", "Жим плечами", "Сгибание рук", "Разгибание трицепса"],
    "Тренировка B": ["Жим ногами", "Становая тяга", "Подтягивания", "Отжимания на брусьях", "Скручивания", "Икроножные"],
    "Тренировка C": ["Наклонный жим", "Выпады", "Тяга верхнего блока", "Разведение рук", "Молотки", "Пресс"],
    "Тренировка D": ["Гакк-приседания", "Румынская тяга", "Гребля", "Подъемы в стороны", "Бицепс на скамье", "Пуловер"]
}

DATA_FILE = 'workout_data.csv'

# Функции для работы с данными
def load_data():
    gist_id = os.environ.get('GIST_ID')
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not gist_id or not github_token:
        if os.path.exists(DATA_FILE):
            return pd.read_csv(DATA_FILE)
        else:
            return pd.DataFrame(columns=['Дата', 'Тренировка', 'Упражнение', 'Подход', 'Повторения', 'Вес'])
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            gist_data = response.json()
            if 'workout_data.csv' in gist_data['files']:
                content = gist_data['files']['workout_data.csv']['content']
                return pd.read_csv(StringIO(content))
        
        # Если что-то пошло не так, возвращаем пустой DataFrame
        return pd.DataFrame(columns=['Дата', 'Тренировка', 'Упражнение', 'Подход', 'Повторения', 'Вес'])
    
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {e}")
        return pd.DataFrame(columns=['Дата', 'Тренировка', 'Упражнение', 'Подход', 'Повторения', 'Вес'])

def save_data(df):
    # Сначала сохраняем локально как резервную копию
    df.to_csv(DATA_FILE, index=False)
    
    # Затем пытаемся сохранить в GitHub Gist
    save_data_to_gist(df)

def save_data_to_gist(df):
    gist_id = os.environ.get('GIST_ID')
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not gist_id or not github_token:
        st.warning("Gist ID или GitHub Token не настроены. Данные сохранены только локально.")
        return
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    payload = {
        "files": {
            "workout_data.csv": {
                "content": df.to_csv(index=False)
            }
        }
    }
    
    try:
        response = requests.patch(
            f'https://api.github.com/gists/{gist_id}',
            headers=headers,
            data=json.dumps(payload)
        )
        
        if response.status_code != 200:
            st.error(f"Ошибка при сохранении данных в Gist: {response.status_code}")
    except Exception as e:
        st.error(f"Ошибка при сохранении данных: {e}")

def add_workout_data(date, workout, exercise, set_num, reps, weight):
    df = load_data()
    new_row = pd.DataFrame({
        'Дата': [date],
        'Тренировка': [workout],
        'Упражнение': [exercise],
        'Подход': [set_num],
        'Повторения': [reps],
        'Вес': [weight]
    })
    df = pd.concat([df, new_row], ignore_index=True)
    save_data(df)
    return df

def get_workout_dates(data):
    """Получить даты тренировок с информацией о типе тренировки"""
    if data.empty:
        return {}
    
    # Группируем данные по дате и тренировке
    workout_dates = data.groupby(['Дата', 'Тренировка']).size().reset_index()
    workout_dates = workout_dates[['Дата', 'Тренировка']]
    
    # Создаем словарь, где ключи - даты, значения - типы тренировок
    date_workout_dict = {}
    for _, row in workout_dates.iterrows():
        date = row['Дата']
        workout = row['Тренировка']
        date_workout_dict[date] = workout
    
    return date_workout_dict

def get_previous_workout_data(data, workout, exercise):
    """Получить данные предыдущей тренировки для указанного упражнения"""
    if data.empty:
        return None
    
    # Фильтруем данные по тренировке и упражнению
    filtered_data = data[(data['Тренировка'] == workout) & (data['Упражнение'] == exercise)]
    
    if filtered_data.empty:
        return None
    
    # Находим последнюю дату тренировки для этого упражнения
    last_date = filtered_data['Дата'].max()
    
    # Получаем данные этой тренировки
    last_workout_data = filtered_data[filtered_data['Дата'] == last_date]
    
    return last_workout_data

def recommend_next_workout(data):
    """Рекомендовать следующую тренировку на основе истории"""
    if data.empty:
        return "Тренировка A"  # Если нет данных, начинаем с тренировки A
    
    # Получаем уникальные даты тренировок
    workout_dates = get_workout_dates(data)
    
    if not workout_dates:
        return "Тренировка A"
    
    # Получаем последнюю дату тренировки и ее тип
    last_date = max(workout_dates.keys())
    last_workout = workout_dates[last_date]
    
    # Определяем следующую тренировку по циклу
    workout_order = ["Тренировка A", "Тренировка B", "Тренировка C", "Тренировка D"]
    current_index = workout_order.index(last_workout)
    next_index = (current_index + 1) % len(workout_order)
    
    return workout_order[next_index]

# Загрузка данных
data = load_data()

# Заголовок приложения
st.title("Трекер тренировок в зале")

# Боковая панель для выбора режима
mode = st.sidebar.radio("Выберите режим", ["Календарь", "Запись тренировки", "История тренировок", "Анализ прогресса"])

if mode == "Календарь":
    st.header("Календарь тренировок")
    
    # Получаем текущую дату и выбираем месяц
    current_date = datetime.date.today()
    month = st.selectbox("Выберите месяц", 
                         range(1, 13), 
                         index=current_date.month-1, 
                         format_func=lambda x: calendar.month_name[x])
    year = st.selectbox("Выберите год", 
                        range(current_date.year - 1, current_date.year + 2), 
                        index=1)
    
    # Создаем календарь
    cal = calendar.monthcalendar(year, month)
    
    # Получаем данные о тренировках
    workout_dates = get_workout_dates(data)
    
    # Отображаем календарь
    st.write("### Календарь тренировок")
    
    # Названия дней недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    # Создаем таблицу календаря
    cols = st.columns(7)
    for i, day in enumerate(days):
        cols[i].markdown(f"**{day}**")
    
    # Заполняем календарь
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # Проверяем, была ли тренировка в этот день
                if date_str in workout_dates:
                    workout_type = workout_dates[date_str]
                    # Определяем цвет в зависимости от типа тренировки
                    if workout_type == "Тренировка A":
                        bgcolor = "#ff9999"  # Красный
                    elif workout_type == "Тренировка B":
                        bgcolor = "#99ff99"  # Зеленый
                    elif workout_type == "Тренировка C":
                        bgcolor = "#9999ff"  # Синий
                    else:
                        bgcolor = "#ffff99"  # Желтый
                        
                    cols[i].markdown(f"""
                    <div style="background-color: {bgcolor}; padding: 5px; border-radius: 5px; text-align: center;">
                        {day}<br/>{workout_type[10:]}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    cols[i].write(f"{day}")
    
    # Легенда
    st.write("### Легенда")
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown('<div style="background-color: #ff9999; padding: 5px; border-radius: 5px; text-align: center;">Тренировка A</div>', unsafe_allow_html=True)
    col2.markdown('<div style="background-color: #99ff99; padding: 5px; border-radius: 5px; text-align: center;">Тренировка B</div>', unsafe_allow_html=True)
    col3.markdown('<div style="background-color: #9999ff; padding: 5px; border-radius: 5px; text-align: center;">Тренировка C</div>', unsafe_allow_html=True)
    col4.markdown('<div style="background-color: #ffff99; padding: 5px; border-radius: 5px; text-align: center;">Тренировка D</div>', unsafe_allow_html=True)
    
    # Рекомендация следующей тренировки
    next_workout = recommend_next_workout(data)
    st.info(f"Рекомендуемая следующая тренировка: **{next_workout}**")

elif mode == "Запись тренировки":
    st.header("Запись новой тренировки")
    
    # Выбор даты и тренировки
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Дата тренировки", datetime.date.today())
    with col2:
        # Рекомендуем следующую тренировку
        recommended_workout = recommend_next_workout(data)
        workout = st.selectbox("Выберите программу тренировки", 
                               list(WORKOUTS.keys()),
                               index=list(WORKOUTS.keys()).index(recommended_workout))
    
    # Создаем таблицу для ввода данных по всем упражнениям
    st.subheader(f"Упражнения для {workout}")
    
    # Создаем вкладки для каждого упражнения
    tabs = st.tabs([exercise for exercise in WORKOUTS[workout]])
    
    for i, exercise in enumerate(WORKOUTS[workout]):
        with tabs[i]:
            # Получаем данные предыдущей тренировки
            prev_workout_data = get_previous_workout_data(data, workout, exercise)
            
            # Определяем количество подходов (по умолчанию 3, но можно изменить)
            sets = st.number_input(f"Количество подходов", min_value=1, max_value=5, value=3, key=f"sets_{exercise}")
            
            # Создаем контейнер для подходов
            for set_num in range(1, sets + 1):
                st.write(f"### Подход {set_num}")
                
                # Значения по умолчанию из предыдущей тренировки
                default_reps = 10
                default_weight = 20.0
                
                if prev_workout_data is not None and not prev_workout_data.empty:
                    # Находим данные для этого подхода
                    set_data = prev_workout_data[prev_workout_data['Подход'] == set_num]
                    if not set_data.empty:
                        default_reps = int(set_data.iloc[0]['Повторения'])
                        default_weight = float(set_data.iloc[0]['Вес'])
                
                # Статус подхода (выполнен или нет)
                set_status = st.checkbox(f"Подход выполнен", key=f"{exercise}_status_{set_num}")
                
                if set_status:
                    # Если подход выполнен, показываем поля для ввода данных
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        reps = st.number_input(f"Повторения", 
                                              min_value=1, 
                                              max_value=100, 
                                              value=default_reps, 
                                              key=f"{exercise}_reps_{set_num}")
                    with col2:
                        weight = st.number_input(f"Вес (кг)", 
                                                min_value=0.0, 
                                                max_value=500.0, 
                                                value=default_weight,
                                                step=2.5, 
                                                key=f"{exercise}_weight_{set_num}")
                    
                    # Меняем стиль, чтобы показать, что подход выполнен
                    st.markdown("""
                    <style>
                    div[data-testid="stCheckbox"]:has(input:checked) + div {
                        background-color: #d4f7d4;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                else:
                    # Если подход не выполнен, показываем данные предыдущей тренировки
                    st.info(f"Предыдущий результат: {default_reps} повторений × {default_weight} кг")
                    # Скрытые поля для сохранения значений
                    reps = st.number_input(f"Повторения (скрыто)", 
                                          min_value=1, 
                                          max_value=100, 
                                          value=default_reps, 
                                          key=f"{exercise}_hidden_reps_{set_num}",
                                          label_visibility="collapsed")
                    weight = st.number_input(f"Вес (скрыто)", 
                                            min_value=0.0, 
                                            max_value=500.0, 
                                            value=default_weight,
                                            step=2.5, 
                                            key=f"{exercise}_hidden_weight_{set_num}",
                                            label_visibility="collapsed")
            
            # Кнопка для сохранения данных для этого упражнения
            if st.button(f"Сохранить {exercise}", key=f"save_{exercise}", type="primary"):
                # Сохраняем только выполненные подходы
                saved = False
                for set_num in range(1, sets + 1):
                    # Проверяем статус подхода
                    set_status = st.session_state.get(f"{exercise}_status_{set_num}", False)
                    if set_status:
                        # Получаем значения из соответствующих полей
                        reps = st.session_state.get(f"{exercise}_reps_{set_num}", default_reps)
                        weight = st.session_state.get(f"{exercise}_weight_{set_num}", default_weight)
                        
                        # Сохраняем данные
                        data = add_workout_data(str(date), workout, exercise, set_num, reps, weight)
                        saved = True
                
                if saved:
                    st.success(f"Данные для {exercise} сохранены!")
                else:
                    st.warning("Нет выполненных подходов для сохранения!")

elif mode == "История тренировок":
    st.header("История тренировок")
    
    # Фильтры
    col1, col2 = st.columns(2)
    with col1:
        workout_filter = st.selectbox("Фильтр по тренировке", ["Все"] + list(WORKOUTS.keys()))
    with col2:
        exercise_filter = st.selectbox("Фильтр по упражнению", ["Все"] + sum(WORKOUTS.values(), []))
    
    # Фильтрация данных
    filtered_data = data.copy()
    if workout_filter != "Все":
        filtered_data = filtered_data[filtered_data['Тренировка'] == workout_filter]
    if exercise_filter != "Все":
        filtered_data = filtered_data[filtered_data['Упражнение'] == exercise_filter]
    
    # Сортировка данных по дате (сначала новые)
    filtered_data = filtered_data.sort_values(by=['Дата', 'Тренировка', 'Упражнение', 'Подход'], ascending=[False, True, True, True])
    
    if not filtered_data.empty:
        # Группируем по дате и тренировке для более удобного просмотра
        unique_date_workouts = filtered_data[['Дата', 'Тренировка']].drop_duplicates()
        
        for _, row in unique_date_workouts.iterrows():
            date_str = row['Дата']
            workout_type = row['Тренировка']
            
            with st.expander(f"{date_str} - {workout_type}"):
                # Показываем данные для этой даты и тренировки
                day_data = filtered_data[(filtered_data['Дата'] == date_str) & 
                                         (filtered_data['Тренировка'] == workout_type)]
                
                # Группируем по упражнениям
                for exercise in sorted(day_data['Упражнение'].unique()):
                    st.write(f"#### {exercise}")
                    
                    # Получаем данные для этого упражнения
                    exercise_data = day_data[day_data['Упражнение'] == exercise]
                    
                    # Создаем таблицу
                    st.table(exercise_data[['Подход', 'Повторения', 'Вес']])
    else:
        st.info("Нет данных для отображения. Записывайте свои тренировки в режиме 'Запись тренировки'.")

else:  # Анализ прогресса
    st.header("Анализ прогресса")
    
    if data.empty:
        st.info("Нет данных для анализа. Начните записывать свои тренировки.")
    else:
        # Выбор упражнения для анализа
        exercise = st.selectbox("Выберите упражнение для анализа", sum(WORKOUTS.values(), []))
        
        # Фильтрация данных по упражнению
        exercise_data = data[data['Упражнение'] == exercise].copy()
        
        if not exercise_data.empty:
            # Преобразуем даты в формат datetime для корректной сортировки
            exercise_data['Дата'] = pd.to_datetime(exercise_data['Дата'])
            exercise_data = exercise_data.sort_values('Дата')
            
            # Вычисляем лучшие показатели для каждой тренировки
            best_results = exercise_data.groupby('Дата').agg({
                'Повторения': 'max',
                'Вес': 'max'
            }).reset_index()
            
            # Преобразуем даты обратно в строки для отображения
            best_results['Дата'] = best_results['Дата'].dt.strftime('%Y-%m-%d')
            exercise_data['Дата'] = exercise_data['Дата'].dt.strftime('%Y-%m-%d')
            
            # График изменения максимального веса
            st.subheader(f"Прогресс по весу - {exercise}")
            fig_weight = px.line(best_results, x='Дата', y='Вес', markers=True,
                                title=f"Изменение максимального веса для {exercise}")
            fig_weight.update_layout(xaxis_title="Дата", yaxis_title="Вес (кг)")
            st.plotly_chart(fig_weight, use_container_width=True)
            
            # График изменения максимальных повторений
            st.subheader(f"Прогресс по повторениям - {exercise}")
            fig_reps = px.line(best_results, x='Дата', y='Повторения', markers=True,
                              title=f"Изменение максимальных повторений для {exercise}")
            fig_reps.update_layout(xaxis_title="Дата", yaxis_title="Повторения")
            st.plotly_chart(fig_reps, use_container_width=True)
            
            # Статистика
            st.subheader("Статистика")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Максимальный вес", f"{best_results['Вес'].max()} кг")
            with col2:
                st.metric("Максимальные повторения", int(best_results['Повторения'].max()))
            with col3:
                if len(best_results) >= 2:
                    first_weight = best_results['Вес'].iloc[0]
                    last_weight = best_results['Вес'].iloc[-1]
                    progress = ((last_weight - first_weight) / first_weight) * 100 if first_weight > 0 else 0
                    st.metric("Прогресс по весу", f"{progress:.1f}%")
                else:
                    st.metric("Прогресс по весу", "Недостаточно данных")
            
            # Таблица с детальными данными по дням
            st.subheader("История тренировок")
            
            # Группируем по датам для удобства просмотра
            unique_dates = sorted(exercise_data['Дата'].unique(), reverse=True)
            
            for date in unique_dates:
                with st.expander(f"Тренировка {date}"):
                    date_data = exercise_data[exercise_data['Дата'] == date]
                    st.table(date_data[['Подход', 'Повторения', 'Вес']])
                    
        else:
            st.info(f"Нет данных для упражнения '{exercise}'")

# Информация о программе
st.sidebar.markdown("---")
st.sidebar.info("""
    **О программе:**
    Трекер тренировок с календарем и анализом прогресса.
    
    Данные сохраняются в GitHub Gist при наличии настроенных
    переменных GIST_ID и GITHUB_TOKEN.
""")

# Добавляем стили для мобильного устройства
st.markdown("""
<style>
    /* Улучшение для мобильных устройств */
    @media (max-width: 768px) {
        .stNumberInput input {
            font-size: 16px;
            height: 40px;
        }
        .stButton button {
            width: 100%;
            height: 50px;
            font-size: 18px;
        }
        .stTabs button {
            font-size: 14px;
        }
        /* Увеличиваем кнопки в календаре */
        div.calendar button {
            min-height: 40px !important;
        }
    }
</style>
""", unsafe_allow_html=True)
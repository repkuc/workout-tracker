import streamlit as st
import pandas as pd
import requests
import json
import os
import datetime
import plotly.express as px

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
                # Используем StringIO для чтения CSV из строки
                from io import StringIO
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

# Загрузка данных
data = load_data()

# Заголовок приложения
st.title("Трекер тренировок в зале")

# Боковая панель для выбора режима
mode = st.sidebar.radio("Выберите режим", ["Запись тренировки", "История тренировок", "Анализ прогресса"])

if mode == "Запись тренировки":
    st.header("Запись новой тренировки")
    
    # Выбор даты и тренировки
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Дата тренировки", datetime.date.today())
    with col2:
        workout = st.selectbox("Выберите программу тренировки", list(WORKOUTS.keys()))
    
    # Создаем таблицу для ввода данных по всем упражнениям
    st.subheader(f"Упражнения для {workout}")
    
    for exercise in WORKOUTS[workout]:
        st.write(f"## {exercise}")
        sets_data = []
        
        cols = st.columns(3)
        sets = cols[0].number_input(f"Количество подходов для {exercise}", min_value=1, max_value=5, value=3, key=f"sets_{exercise}")
        
        for i in range(1, sets + 1):
            col1, col2 = st.columns(2)
            with col1:
                reps = st.number_input(f"Повторения (подход {i})", min_value=1, max_value=100, value=10, key=f"{exercise}_reps_{i}")
            with col2:
                weight = st.number_input(f"Вес, кг (подход {i})", min_value=0.0, max_value=500.0, value=20.0, step=2.5, key=f"{exercise}_weight_{i}")
            sets_data.append((i, reps, weight))
        
        # Показываем последние данные для этого упражнения
        if not data.empty:
            last_workout = data[(data['Тренировка'] == workout) & (data['Упражнение'] == exercise)]
            if not last_workout.empty:
                last_date = last_workout['Дата'].max()
                st.info(f"Последняя тренировка ({last_date}):")
                last_results = last_workout[last_workout['Дата'] == last_date]
                for _, row in last_results.iterrows():
                    st.text(f"Подход {row['Подход']}: {row['Повторения']} повторений × {row['Вес']} кг")

        # Кнопка для сохранения данных для этого упражнения
        if st.button(f"Сохранить данные для {exercise}", key=f"save_{exercise}"):
            for set_num, reps, weight in sets_data:
                data = add_workout_data(str(date), workout, exercise, set_num, reps, weight)
            st.success(f"Данные для {exercise} сохранены!")
    
    # Кнопка для сохранения всей тренировки сразу
    if st.button("Сохранить всю тренировку", type="primary"):
        st.warning("Для сохранения данных используйте кнопки для каждого упражнения")

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
        st.dataframe(filtered_data, use_container_width=True)
        
        # Опция удаления записей
        if st.button("Удалить выбранные записи"):
            st.warning("Функция удаления записей будет добавлена в следующей версии")
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
            # Подготовка данных для графика
            # Вычисляем максимальные значения веса и повторений для каждой даты
            max_values = exercise_data.groupby('Дата').agg({'Вес': 'max', 'Повторения': 'max'}).reset_index()
            
            # График изменения максимального веса
            st.subheader(f"Прогресс по весу - {exercise}")
            fig_weight = px.line(max_values, x='Дата', y='Вес', markers=True)
            st.plotly_chart(fig_weight, use_container_width=True)
            
            # График изменения максимальных повторений
            st.subheader(f"Прогресс по повторениям - {exercise}")
            fig_reps = px.line(max_values, x='Дата', y='Повторения', markers=True)
            st.plotly_chart(fig_reps, use_container_width=True)
            
            # Статистика
            st.subheader("Статистика")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Максимальный вес", f"{max_values['Вес'].max()} кг")
            with col2:
                st.metric("Максимальные повторения", int(max_values['Повторения'].max()))
            with col3:
                if len(max_values) >= 2:
                    first_weight = max_values.iloc[0]['Вес']
                    last_weight = max_values.iloc[-1]['Вес']
                    progress = ((last_weight - first_weight) / first_weight) * 100 if first_weight > 0 else 0
                    st.metric("Прогресс по весу", f"{progress:.1f}%")
                else:
                    st.metric("Прогресс по весу", "Недостаточно данных")
            
            # Таблица с детальными данными
            st.subheader("Все записи для упражнения")
            st.dataframe(exercise_data.sort_values(by=['Дата', 'Подход'], ascending=[False, True]))
        else:
            st.info(f"Нет данных для упражнения '{exercise}'")

# Информация о программе
st.sidebar.markdown("---")
st.sidebar.info("""
    **О программе:**
    Это простое приложение для отслеживания тренировок в зале.
    
    Данные сохраняются в GitHub Gist при наличии настроенных
    переменных окружения GIST_ID и GITHUB_TOKEN или
    локально в файл 'workout_data.csv'.
""")
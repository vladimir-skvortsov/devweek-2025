import csv

count_0 = 0
count_1 = 0
total_len_0 = 0  # Общая длина текстов для is_human=0
total_len_1 = 0  # Общая длина текстов для is_human=1

with open('merged.csv', mode='r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        text = row.get('text', '')  # Получаем текст (пустая строка, если столбца нет)
        is_human = row.get('is_human', '')
        
        if is_human == '0':
            count_0 += 1
            total_len_0 += len(text)
        elif is_human == '1':
            count_1 += 1
            total_len_1 += len(text)

# Считаем среднюю длину
avg_len_0 = total_len_0 / count_0 if count_0 > 0 else 0
avg_len_1 = total_len_1 / count_1 if count_1 > 0 else 0

# Вывод результатов
print(f"Количество строк с is_human=0: {count_0}")
print(f"Количество строк с is_human=1: {count_1}\n")

print(f"Средняя длина текста для is_human=0: {avg_len_0:.2f} символов")
print(f"Средняя длина текста для is_human=1: {avg_len_1:.2f} символов")
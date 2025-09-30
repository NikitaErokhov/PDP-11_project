from my_funcs import parse_comm, recgnz_comm, \
    recgnz_args, bin_to_oct, code_arg, recgnz_mode

# Список для формирования .l файла, здесь [строки .l файла по прорядку]
lines = []
# PC
programm_counter = f'{0:06}'
# Словарь для формирования .о файла, здесь (адрес блока): [байты блока по порядку]
object_lines = dict()
# Адрес текущего блока
curr_block = ''


def code_command(name: str, args: list[str]):
    # Получили кодировку команды в 2-ой системе счисления
    code_n = recgnz_comm(name)
    # Получили dict-ы с ключом mode и ключом reg|const|simb соотв. аргументов
    parse_a = recgnz_args(args) if args else 0
    # Конкатенируем аргументы к коду команды по порядку
    if parse_a:
        for arg_dict in parse_a:
            code_n += code_arg(arg_dict)

    return code_n, parse_a


with open(r'pdp11_tests\01_sum\01_sum.pdp') as file:
    while True:
        # Читаем одну строку
        key = file.readline()
        if key:
            # В непустой лежит команда или проч. - парсим
            str_dict = parse_comm(key)

            # В каком адресе лежит какая команда

            lines.append(programm_counter + ':\t\t' +
                         str_dict['name'] + '\t\t' + ', '.join(str_dict['arg']) + '\n')

            # Специально для . =, чтобы праивльно следить за PC и байтами для .o
            if str_dict['name'] == '. =':
                programm_counter = f"{(int(programm_counter, 8) +
                                       int(str_dict['arg'][0], 8)):06o}"
                curr_block = f"{int(programm_counter, 8):04x}"
                object_lines[curr_block] = list()
                continue
            # Выделяем имя и аргументы
            comm_code, parse_a = code_command(name=str_dict['name'],
                                              args=str_dict['arg'])
            # Команда хранится в закодированном виде:
            lines.append('\t'+bin_to_oct(comm_code)+'\n')
            # Команда в виде двух байтов
            object_lines[curr_block] += [f"{int(comm_code[8:], 2):02x}\n",
                                         f'{int(comm_code[:8], 2):02x}\n']
            # PC += 2
            programm_counter = f"{(int(programm_counter, 8) + 2):06o}"
            # Обрабатываем аргументы и их моды (специфику моды)
            if parse_a:
                for arg_dict in parse_a:
                    bin_line, raise_PC = recgnz_mode(arg_dict)
                    if raise_PC:
                        # если есть чего-нибудь специфичного, то
                        lines.append('\t'+bin_to_oct(bin_line)+'\n')
                        programm_counter = f"{(int(programm_counter, 8) + 2):06o}"
                        object_lines[curr_block] += [f"{int(bin_line[8:], 2):02x}\n",
                                                     f'{int(bin_line[:8], 2):02x}\n']
        else:
            lines.append(programm_counter + ':\t')
            break
    file.close()

# Формируем .l и .o из собранной информации

with open(r'pdp11_tests\01_sum\01_sum.pdp.l', mode='a') as file:
    for key in lines:
        file.write(key)
    file.close()

with open(r'pdp11_tests\01_sum\01_sum.pdp.o', mode='a') as file:
    for key in object_lines.keys():
        file.write(key + ' ' + f'{len(object_lines[key]):04x}\n')
        for byte in object_lines[key]:
            file.write(byte)
    file.close()

import os
import requests
import json
import xmltodict

FILES_DIR = './files/'


def cme_get_token(api_login=None, api_password=None):
    """Получение токена по кредам"""
    if api_login is None:
        api_login = input('Введите API логин СМЕ: ')
    if api_password is None:
        api_password = input('Введите API пароль СМЕ: ')

    try:
        url = 'https://lk.cm.expert/oauth/token'
        payload = {
            'grant_type': 'client_credentials',
            'client_id': {api_login},
            'client_secret': {api_password}
        }
        response = requests.post(
            url=url,
            data=payload
        )
        status_code = response.status_code
        if status_code != 200:
            return None
        token = response.json()['access_token']
        return token
    except:
        return None


def cme_get_car_info(CME_TOKEN, value, field='vin', stockState='in'):
    """Получение dmsCarId и dealerId по field:
    - VIN
    - id
    """
    try:
        url = f'https://lk.cm.expert/api/v1/dealers/dms/cars?'\
            f'filter[{field}][eq]={value}'\
            f'&filter[stockState][eq]={stockState}'
        headers = {
            'Authorization': f'Bearer {CME_TOKEN}',
        }
        response = requests.request(
            'GET',
            url,
            headers=headers
        ).json()[0]
    except Exception as error:
        print(error)
        response = None
    return response


def cme_delete_car(CME_TOKEN, dealerId, dmsCarId):
    """Удаление авто со склада по dmsCarId"""
    try:
        url = f'https://lk.cm.expert/api/v1/dealers/{dealerId}/'\
            f'dms/cars/{dmsCarId}'
        headers = {
            'Authorization': f'Bearer {CME_TOKEN}',
        }
        response = requests.request(
            'DELETE',
            url,
            headers=headers
        )
        response_code = response.status_code
        if response_code != 200:
            return False
    except:
        return False
    return True


def cme_create_car(CME_TOKEN, dealerId, dmsCarId, payload):
    """Создание авто на складе"""
    url = f'https://lk.cm.expert/api/v1/dealers/{dealerId}/dms/cars/{dmsCarId}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CME_TOKEN}'
    }
    response = requests.request(
        "PUT",
        url,
        headers=headers,
        data=json.dumps(payload)
    )
    response_code = response.status_code
    if response_code == 201:
        return True
    return False


def cme_update_car_info(CME_TOKEN, dealerId, dmsCarId, payload):
    """Обновление данных авто в СМЕ"""
    try:
        url = f'https://lk.cm.expert/api/v1/dealers/{dealerId}/dms/cars/{dmsCarId}'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {CME_TOKEN}',
        }
        response = requests.request(
            "PATCH",
            url,
            headers=headers,
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            return True
        else:
            print(response.text)
            return False  
    except:
        return False 


def replace_with_chage_stock_type():
    """Перемещение авто по списку с изменением типа стока
    
    1. Открыть txt со списком dmsCarId
    2. Получить GETом все данные из текущего авто
    3. Заменить данные на searching
    4. Удалить авто
    5. Создать этот авто на новом складе"""

    # Получить вводные данные
    CME_TOKEN = cme_get_token()
    dealerId_finish = input('Введите dealerId, где должны оказаться '\
                            'авто после перемещения: ')

    # Открыть txt со списком dmsCarId
    input('Внесите в файл /files/dmsCarId_list.txt список dmsCarId, которые '\
          'необходимо перенести (кадый dmsCarId с новой строки) и нажмите '\
          'Enter ')
    dmsCarId_list_file_name = 'dmsCarId_list.txt'
    dmsCarId_file = open(f'{FILES_DIR}{dmsCarId_list_file_name}')
    dmsCarId_list = []
    for dmsCarId in dmsCarId_file:
        dmsCarId = dmsCarId.replace('\n', '')
        dmsCarId_list.append(dmsCarId)

    counter = 0
    counter_total = len(dmsCarId_list)
    for dmsCarId in dmsCarId_list:
        counter += 1
        # Получить GETом все данные из текущего авто
        dmsCarId_info = cme_get_car_info(CME_TOKEN, dmsCarId, field='dmsCarId', stockState='in')

        # Заменить данные на searching
        brand = dmsCarId_info.get('brand')
        model = dmsCarId_info.get('model')
        pseudoModel = dmsCarId_info.get('pseudoModel')
        generation = dmsCarId_info.get('generation')
        modificationName = dmsCarId_info.get('modificationName')
        equipmentName = dmsCarId_info.get('equipmentName')

        if brand is not None:
            dmsCarId_info['searchingBrand'] = brand
        if model is not None:
            dmsCarId_info['searchingModel'] = model
        if pseudoModel is not None:
            dmsCarId_info['searchingPseudoModel'] = pseudoModel
        if generation is not None:
            dmsCarId_info['searchingGeneration'] = generation
        if modificationName is not None:
            dmsCarId_info['searchingModificationName'] = modificationName
        if equipmentName is not None:
            dmsCarId_info['searchingEquipmentName'] = equipmentName

        # Удалить авто
        dealerId_start = dmsCarId_info.get('dealerId')
        cme_delete_car(CME_TOKEN, dealerId_start, dmsCarId)

        # Создать этот авто на новом складе
        create_result = cme_create_car(CME_TOKEN, dealerId_finish, dmsCarId, dmsCarId_info)
        if create_result:
            print(f'{counter}/{counter_total}: {dmsCarId} - перемещен')
        else:
            print(f'{counter}/{counter_total}: {dmsCarId} - возникла ошибка')


def update_photos_cme_car_from_avito_feed():
    """Обновление данных авто в СМЕ из фида Авито"""
    
    CME_TOKEN = cme_get_token()
    feed_name = input('Переместите фид формата Avito в папку "files" и введите название фида без ".xml": ')

    # Распарсить фид Авито
    feed = open(f'{FILES_DIR}{feed_name}.xml', 'rb')
    feed_dict = xmltodict.parse(feed).get('Ads').get('Ad')

    # Словарь для загрузки данных 
    payload = {}

    counter = 0
    counter_total = len(feed_dict)
    for car in feed_dict:
        counter += 1

        # Получить VIN
        try:
            vin = car.get('VIN')
        except:
            vin = None

        # В фиде может не быть тега фотографий
        photosUrls = []
        try:
            images = car.get('Images').get('Image')
            for image in images:
                image = image.get('@url')
                photosUrls.append(image)
        except:
            print(f'{vin} - нет фото')
        if len(photosUrls) >= 1:
            payload['photosUrls'] = photosUrls

        # Найти авто на складе СМЕ
        cme_car_info = cme_get_car_info(CME_TOKEN, vin)
        if cme_car_info is None:
            """TODO: проверять наличие авто по номеру кузова"""
            print(f'{counter}/{counter_total}: {vin} - В СМЕ нет такого авто')
            continue
        dmsCarId = cme_car_info.get('dmsCarId')
        dealerId = cme_car_info.get('dealerId')

        # Обновление описания в СМЕ
        update_result = cme_update_car_info(CME_TOKEN, dealerId, dmsCarId, payload)
        print(f'{counter}/{counter_total}: {vin} - {update_result}')


def menu():
    """Меню функций"""
    print("""
    ДОСТУПНЫЕ ИНСТРУМЕНТЫ
    1 - переместить авто со сменой типа стока
    2 - перенести фотографии из фида авито в авто на складе
    """)
    while True:
        task = input('Введите номер функции и нажмите Enter: ')
        if task == '1':
            replace_with_chage_stock_type()
        elif task == '2':
            update_photos_cme_car_from_avito_feed()
        else:
            print('Нужно ввести номер одной из команд')

if __name__ == '__main__':
    menu()

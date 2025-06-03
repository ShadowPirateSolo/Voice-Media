import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.types import BufferedInputFile
from aiogram.filters import Command, or_f
from gtts import gTTS
import edge_tts
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
import ffmpeg
import speech_recognition as sr
import platform
from setup_ffmpeg import setup_ffmpeg

setup_ffmpeg()
if platform.system() == 'Windows':
    os.environ["FFMPEG_BINARY"] = os.path.join("bin", "ffmpeg.exe")
else:
    os.environ["FFMPEG_BINARY"] = os.path.join("bin", "ffmpeg")


async def run_ffmpeg(args: list):
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await process.communicate()


user_texts = {}
user_photos = {}
user_audios = {}
user_videos = {}

load_dotenv()
token = os.getenv('token')
admin_username = os.getenv('admin_username')
bot = Bot(token=token)

dp = Dispatcher()


async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="help", description="Помощь")
    ])


@dp.message(Command('start'))
async def start_handler(message: Message):
    await message.answer(f'Здравствуй, {message.chat.first_name}. Добро пожаловать в бота для обработки медиа файлов! '
                         f'Для того, чтобы им пользоваться нужно просто отправить сообщение, которое вы хотите '
                         f'обработать в чат и выбрать нужное действие в появившемся меню. '
                         f'Для более подробной информации воспользуйтесь командой /help')


@dp.message(Command('help'))
async def help_handler(message: Message):
    help_text = ('Бот умеет:\n'
                 '1) озвучивать текст различными голосами и считать его длину;\n'
                 '2) делать фото черно-белыми, зеркалить их по вертикали и горизонтали, '
                 'сокращать количество цветов на фото, размывать их, а также получать негатив фото и '
                 'сокращать на них количество цветов до 16;\n'
                 '3) ускорять и замедлять аудио, делать реверс аудио, а также распознавать в них текст;\n'
                 '4) делать видео черно-белыми, делать реверс видео, преобразовывать видео к формату GIF, '
                 'а также отделять аудио от видео.\n'
                 'Для обработки медиафайла или текста, просто отправьте его в чат бота и следуйте инструкции'
                 ' на появившейся клавиатуре.\n'
                 'Исходный код бота можно найти на сайте https://github.com/ShadowPirateSolo/Voice-Media.')
    await message.answer(help_text)


statistics = {}
@dp.message(Command('statistics'))
async def statistics_handler(message: Message):
    if message.from_user.username == admin_username:
        def requests(n):
            if n % 100 // 10 == 1 or n % 10 in {0, 5, 6, 7, 8, 9}:
                return 'запросов'
            elif n % 10 == 1:
                return 'запрос'
            else:
                return 'запроса'


        answer = 'Текущие пользователи:\n'
        for username in statistics.keys():
            answer += f'@{username} - {statistics[username]} {requests(statistics[username])}\n'

        await message.answer(answer)


@dp.message(F.text)
async def text_handler(message: Message):
    if message.from_user.username in statistics.keys():
        statistics[message.from_user.username] += 1
    else:
        statistics[message.from_user.username] = 1

    user_texts[message.chat.id] = message.text
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Озвучить', callback_data=f'text_voice')],
            [InlineKeyboardButton(text='Посчитать количество слов', callback_data=f'text_lenth')]
        ]
    )
    await message.answer('Выберите действие с текстом:', reply_markup=keyboard)


@dp.callback_query(F.data == 'text_lenth')
async def text_lenth(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    if callback.message.chat.id not in user_texts.keys():
        return


    def words(n):
        if n % 100 // 10 == 1 or n % 10 in {0, 5, 6, 7, 8, 9}:
            return 'слов'
        elif n % 10 == 1:
            return 'слово'
        else:
            return 'слова'


    text = user_texts[callback.message.chat.id]
    text = text.replace('-', '')
    lenth = len(text.split())
    await callback.message.answer(f'В вашем тексте {lenth} {words(lenth)}')
    await callback.answer()
    del user_texts[callback.message.chat.id]


@dp.callback_query(F.data == 'text_voice')
async def text_voice(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    if callback.message.chat.id not in user_texts.keys():
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Русский', callback_data='gtts_language:ru')],
            [InlineKeyboardButton(text='Английский', callback_data='gtts_language:en')],
            [InlineKeyboardButton(text='Немецкий', callback_data='gtts_language:de')],
            [InlineKeyboardButton(text='Французский', callback_data='gtts_language:fr')],
            [InlineKeyboardButton(text='Испанский', callback_data='gtts_language:es')],
            [InlineKeyboardButton(text='Польский', callback_data='gtts_language:pl')],
            [InlineKeyboardButton(text='Более реалистичный голос', callback_data=f'real_voice')]
        ]
    )
    await callback.message.answer('Выберите голос для озвучки этого текста:', reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == 'real_voice')
async def real_voice(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    if callback.message.chat.id not in user_texts.keys():
        return

    file = f'voice_{callback.message.chat.id}.mp3'

    communicate = edge_tts.Communicate(
        text=user_texts[callback.message.chat.id],
        voice="ru-RU-DmitryNeural"
    )
    await communicate.save(file)

    voice = FSInputFile(file)
    await callback.message.answer_voice(voice)

    os.remove(file)
    await callback.answer()
    del user_texts[callback.message.chat.id]


@dp.callback_query(F.data.startswith('gtts_language'))
async def gtts_voice(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    if callback.message.chat.id not in user_texts.keys():
        return

    text = user_texts[callback.message.chat.id]
    file = f'voice_{callback.message.chat.id}.mp3'
    lang = callback.data.split(':')[1]

    tts = gTTS(text, lang=lang)
    tts.save(file)


    voice = FSInputFile(file)
    await callback.message.answer_voice(voice)

    os.remove(file)
    await callback.answer()
    del user_texts[callback.message.chat.id]


@dp.message(F.photo)
async def photo_handler(message: Message):
    if message.from_user.username in statistics.keys():
        statistics[message.from_user.username] += 1
    else:
        statistics[message.from_user.username] = 1

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    data = await bot.download_file(file.file_path)
    image_bytes = data.read()
    image = Image.open(BytesIO(image_bytes))

    user_photos[message.chat.id] = image

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Сделать черно-белым', callback_data='photo_black-white')],
            [InlineKeyboardButton(text='Отзеркалить по горизонтали', callback_data='photo_mirror-horizontal')],
            [InlineKeyboardButton(text='Отзеркалить по вертикали', callback_data='photo_mirror-vertical')],
            [InlineKeyboardButton(text='Негатив', callback_data='photo_negative')],
            [InlineKeyboardButton(text='Сократить цвета', callback_data='photo_reduce-colors')],
            [InlineKeyboardButton(text='Размыть', callback_data='photo_blur')],
            [InlineKeyboardButton(text='Сделать квадратным', callback_data='photo_square')]
        ]
    )
    await message.answer('Выберите действие с фото:', reply_markup=keyboard)


@dp.callback_query(F.data == 'photo_black-white')
async def black_white(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    bw_image = image.convert('L')

    output = BytesIO()
    bw_image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="black_white.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_mirror-horizontal')
async def mirror_vertical(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    mh_image = image.transpose(Image.FLIP_LEFT_RIGHT)

    output = BytesIO()
    mh_image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="mirror_horizontal.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_mirror-vertical')
async def mirror_horizontal(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    mh_image = image.transpose(Image.FLIP_TOP_BOTTOM)

    output = BytesIO()
    mh_image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="mirror_vertical.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_negative')
async def negative(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    image = ImageOps.invert(image)

    output = BytesIO()
    image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="negative.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_reduce-colors')
async def reduce_colors(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    image = image.quantize(colors=16).convert('RGB')

    output = BytesIO()
    image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="reduce_colors.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_blur')
async def blur(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    image = image.filter(ImageFilter.GaussianBlur(16))

    output = BytesIO()
    image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="blur.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.callback_query(F.data == 'photo_square')
async def square(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_photos.keys():
        return

    image = user_photos[callback.message.chat.id]
    image = image.resize((1000, 1000))

    output = BytesIO()
    image.save(output, format='JPEG')
    output.seek(0)
    photo = BufferedInputFile(output.read(), filename="square.jpg")
    await callback.message.answer_photo(photo)

    del user_photos[callback.message.chat.id]
    await callback.answer()


@dp.message(or_f(F.audio, F.voice))
async def audio_handler(message: Message):
    if message.from_user.username in statistics.keys():
        statistics[message.from_user.username] += 1
    else:
        statistics[message.from_user.username] = 1

    duration = message.audio.duration if message.audio else message.voice.duration
    if duration > 600:
        await message.answer("Аудио слишком длинное. Максимальная длина — 10 минут.")
        return

    file_id = message.audio.file_id if message.audio else message.voice.file_id
    file = await bot.get_file(file_id)
    data = await bot.download_file(file.file_path)

    original_ext = 'mp3' if message.audio else 'ogg'
    original_path = f"{message.chat.id}_original.{original_ext}"

    with open(original_path, "wb") as f:
        f.write(data.read())

    mp3_path = f"{message.chat.id}.mp3"
    (
        ffmpeg
        .input(original_path)
        .output(mp3_path, format='mp3')
        .overwrite_output()
        .run(quiet=True)
    )

    os.remove(original_path)

    user_audios[message.chat.id] = mp3_path

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Реверс аудио', callback_data='audio_reverse')],
            [InlineKeyboardButton(text='Ускорить в 2 раза', callback_data='audio_x2')],
            [InlineKeyboardButton(text='Замедлить в 2 раза', callback_data='audio_x0.5')],
            [InlineKeyboardButton(text='Расшифровать речь', callback_data='audio_tt')]
        ]
    )
    await message.answer("Выберите действие с аудио:", reply_markup=keyboard)


@dp.callback_query(F.data == "audio_reverse")
async def audio_reverse(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_audios.keys():
        return
    processing_message = await callback.message.answer('Обработка аудио...')

    input_path = user_audios[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}_reversed.mp3"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-af', 'areverse',
        output_path
    ])

    os.remove(input_path)
    del user_audios[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    audio = FSInputFile(output_path)
    await callback.message.answer_voice(audio)

    os.remove(output_path)


@dp.callback_query(F.data == "audio_x2")
async def audio_speedup(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_audios.keys():
        return
    processing_message = await callback.message.answer('Обработка аудио...')

    input_path = user_audios[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}_faster.mp3"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-af', 'atempo=2.0',
        output_path
    ])

    os.remove(input_path)
    del user_audios[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    audio = FSInputFile(output_path)
    await callback.message.answer_voice(audio)

    os.remove(output_path)


@dp.callback_query(F.data == "audio_x0.5")
async def audio_slowdown(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_audios.keys():
        return
    processing_message = await callback.message.answer('Обработка аудио...')

    input_path = user_audios[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}_slower.mp3"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-af', 'atempo=0.5',
        output_path
    ])

    os.remove(input_path)
    del user_audios[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    audio = FSInputFile(output_path)
    await callback.message.answer_voice(audio)

    os.remove(output_path)


@dp.callback_query(F.data == "audio_tt")
async def audio_transcribe(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_audios.keys():
        return
    processing_message = await callback.message.answer('Обработка аудио...')

    chat_id = callback.message.chat.id
    input_path = user_audios.get(chat_id)

    wav_path = input_path.rsplit('.', 1)[0] + "_converted.wav"

    ffmpeg.input(input_path).output(
        wav_path,
        format='wav',
        acodec='pcm_s16le',
        ar='16000',
        ac=1
    ).run(overwrite_output=True, quiet=True)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data, language="ru-RU")
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)
        await callback.message.answer(f"Распознанный текст:\n{text}")
    except Exception:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)
        await callback.message.answer(f"Не удалось распознать текст")

    os.remove(input_path)
    del user_audios[callback.message.chat.id]

    os.remove(wav_path)


@dp.message(F.video)
async def video_handler(message: Message):
    try:
        if message.from_user.username in statistics.keys():
            statistics[message.from_user.username] += 1
        else:
            statistics[message.from_user.username] = 1

        video = message.video
        if video.duration and video.duration > 180:
            await message.answer("Видео слишком длинное. Максимально возможная длина — 3 минуты.")
            return

        file = await bot.get_file(video.file_id)
        data = await bot.download_file(file.file_path)

        video_path = f"{message.chat.id}_video.mp4"
        with open(video_path, "wb") as f:
            f.write(data.read())

        user_videos[message.chat.id] = video_path

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text='Сделать черно-белым', callback_data='video_bw')],
                [InlineKeyboardButton(text='Реверс видео', callback_data='video_reverse')],
                [InlineKeyboardButton(text='Сохранить в формате GIF', callback_data='video_gif')],
                [InlineKeyboardButton(text='Извлечь аудиодорожку', callback_data='video_audio')]
            ]
        )
        await message.answer("Выберите действие с видео:", reply_markup=keyboard)
    except TelegramBadRequest:
        await message.answer('Бот не может обработать это видео, потому что оно весит больше 20 Мб.')


@dp.callback_query(F.data == 'video_bw')
async def video_black_white(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_videos.keys():
        return
    processing_message = await callback.message.answer('Обработка видео...')

    input_path = user_videos[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}_bw.mp4"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-vf', 'hue=s=0',
        '-vcodec', 'libx264', '-acodec', 'aac', '-strict', 'experimental',
        output_path
    ])

    os.remove(input_path)
    del user_videos[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    video = FSInputFile(output_path)
    await callback.message.answer_video(video)

    os.remove(output_path)


@dp.callback_query(F.data == 'video_reverse')
async def video_reverse(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_videos.keys():
        return
    processing_message = await callback.message.answer('Обработка видео...')

    input_path = user_videos[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}_reverse.mp4"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-vf', 'reverse', '-af', 'areverse',
        output_path
    ])

    os.remove(input_path)
    del user_videos[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    video = FSInputFile(output_path)
    await callback.message.answer_video(video)

    os.remove(output_path)


@dp.callback_query(F.data == 'video_gif')
async def video_to_gif(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_videos.keys():
        return
    processing_message = await callback.message.answer('Обработка видео...')

    input_path = user_videos[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}.gif"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-vf', 'fps=15,scale=320:-1:flags=lanczos',
        '-loop', '0',
        output_path
    ])

    os.remove(input_path)
    del user_videos[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    gif = FSInputFile(output_path)
    await callback.message.answer_document(gif)

    os.remove(output_path)


@dp.callback_query(F.data == 'video_audio')
async def video_extract_audio(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    if callback.message.chat.id not in user_videos.keys():
        return
    processing_message = await callback.message.answer('Обработка видео...')

    input_path = user_videos[callback.message.chat.id]
    output_path = f"{callback.message.chat.id}.mp3"

    await run_ffmpeg([
        'ffmpeg', '-i', input_path,
        '-f', 'mp3', '-acodec', 'libmp3lame',
        output_path
    ])

    os.remove(input_path)
    del user_videos[callback.message.chat.id]
    await bot.delete_message(chat_id=callback.message.chat.id, message_id=processing_message.message_id)

    audio = FSInputFile(output_path)
    await callback.message.answer_audio(audio)

    os.remove(output_path)


async def main():
    await set_bot_commands()
    await dp.start_polling(bot)


if __name__ == '__main__':
    print('Бот запущен')
    asyncio.run(main())
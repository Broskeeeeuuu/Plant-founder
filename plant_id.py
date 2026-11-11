import base64
import io
import json
import os

import anthropic
import streamlit as st
from PIL import Image

MODEL = "claude-sonnet-5-5"

PROMPT = """Ты — ботаник и эксперт по уходу за растениями. Определи растение на фото.
Верни ТОЛЬКО JSON без markdown и пояснений, на русском языке:
{"is_plant": true, "name": "русское название", "latin": "латинское название",
 "confidence": "высокая|средняя|низкая", "about": "1-2 предложения о растении",
 "care": {"light": "свет", "water": "полив и частота",
          "climate": "температура и влажность", "soil": "грунт и пересадка",
          "feed": "подкормка"},
 "problems": ["типичные проблемы и признаки"],
 "toxic": "токсичность для кошек, собак и людей",
 "alt": ["1-2 похожих варианта, если уверенность не высокая"],
 "visible_issues": "проблемы, заметные на фото (или пустая строка)"}
Если на фото нет растения: {"is_plant": false}."""


def prepare_image(file):
    img = Image.open(file).convert("RGB")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def identify(image_b64, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    text = response.content[0].text
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def show_result(d):
    if not d.get("is_plant"):
        st.warning("Растение на фото не найдено. Снимите крупнее и при хорошем свете.")
        return

    st.header(d.get("name", "Неизвестно"))
    st.caption(d.get("latin", "") + " · Уверенность: " + d.get("confidence", "—"))
    st.write(d.get("about", ""))
    if d.get("alt"):
        st.write("Возможно также: " + ", ".join(d["alt"]))

    care = d.get("care", {})
    st.subheader("Уход")
    st.markdown("☀️ **Свет:** " + care.get("light", "—"))
    st.markdown("💧 **Полив:** " + care.get("water", "—"))
    st.markdown("🌡️ **Температура и влажность:** " + care.get("climate", "—"))
    st.markdown("🪴 **Грунт и пересадка:** " + care.get("soil", "—"))
    st.markdown("🧪 **Подкормка:** " + care.get("feed", "—"))

    st.subheader("Частые проблемы")
    for p in d.get("problems", []):
        st.markdown("⚠️ " + p)
    if d.get("visible_issues"):
        st.info("🔍 На вашем фото: " + d["visible_issues"])
    st.markdown("🐾 **Токсичность:** " + d.get("toxic", "—"))


st.set_page_config(page_title="Определитель растений", page_icon="🌿")
st.title("🌿 Определитель растений")
st.write("Сфотографируйте растение — получите название и советы по уходу.")

api_key = os.environ.get("ANTHROPIC_API_KEY") or st.sidebar.text_input(
    "Ключ Anthropic API", type="password"
)

source = st.radio("Источник фото", ["Загрузить файл", "Камера"], horizontal=True)
if source == "Камера":
    photo = st.camera_input("Снимок растения")
else:
    photo = st.file_uploader("Фото растения", type=["jpg", "jpeg", "png", "webp"])

if photo:
    st.image(photo)
    if st.button("Определить растение", type="primary"):
        if not api_key:
            st.error("Введите ключ API в боковой панели слева.")
        else:
            with st.spinner("Анализирую…"):
                try:
                    result = identify(prepare_image(photo), api_key)
                    show_result(result)
                except anthropic.APIError as e:
                    st.error("Ошибка API: " + str(e))
                except Exception as e:
                    st.error("Ошибка: " + str(e))

import asyncio
import random
from playwright.async_api import async_playwright
import base64
import cv2
import numpy as np
#  linux系统下的浏览器
# executable_path = "/usr/bin/chromium-browser"
# windows系统下的浏览器
executable_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# executable_path = "D:\\chrome-win64\\chrome.exe"
# linux下需要使用无头模式
# headless = True  # 无头模式
headless = False
mt_username = 'xxxx'
mt_password = 'xxx'
xc_username = 'xxx'
xc_password = 'xxx'
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
args = ["--disable-blink-features=AutomationControlled"]


async def fill_input(input, text):
    for char in text:
        await input.type(char)
        await asyncio.sleep(0.1)


async def delay(n=1):
    ms = random.uniform(0.1, n)
    await asyncio.sleep(ms)


async def get_slider_position(background_image_base64, slider_image_base64):
    """
    使用模板匹配找出滑块在背景图中的位置。

    Args:
        background_image_base64 (str): 背景图像的base64编码。
        slider_image_base64 (str): 滑块图像的base64编码。

    Returns:
        tuple: 滑块在背景图中的位置 (x, y)。
    """
    # 解码base64图像
    bg_img_data = base64.b64decode(background_image_base64)
    slider_img_data = base64.b64decode(slider_image_base64)

    # 将图像数据转换为numpy数组
    bg_img_array = np.frombuffer(bg_img_data, dtype=np.uint8)
    slider_img_array = np.frombuffer(slider_img_data, dtype=np.uint8)

    # 使用OpenCV读取图像
    bg_img = cv2.imdecode(bg_img_array, cv2.IMREAD_GRAYSCALE)  # 转换为灰度图像
    bg_img = cv2.resize(bg_img, (360, 180))  # 将背景图像拉伸到360x180

    slider_img = cv2.imdecode(
        slider_img_array, cv2.IMREAD_UNCHANGED)  # 读取包含alpha通道的图像

    # 找到滑块图像中的非透明像素
    _, _, _, alpha = cv2.split(slider_img)
    non_zero_pixels = cv2.findNonZero(alpha)

    # 计算滑块左边的留白宽度
    left_margin = np.min(non_zero_pixels[:, :, 0])

    # 使用模板匹配找出滑块在背景图中的位置
    result = cv2.matchTemplate(bg_img, cv2.cvtColor(
        slider_img, cv2.COLOR_BGRA2GRAY), cv2.TM_CCOEFF_NORMED)  # 将滑块图像转换为灰度图像
    _, _, _, max_loc = cv2.minMaxLoc(result)

    # max_loc 就是滑块在背景图中的位置，加上滑块的宽度和左边的留白宽度
    return (max_loc[0] + left_margin, max_loc[1])


async def login_xc():
    """
    登录携程
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless,
                                          executable_path=executable_path,
                                          args=args
                                          )
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        try:
            await page.goto("https://ebooking.ctrip.com/login/index")
            await delay()

            username = await page.query_selector('[name="username-input"]')
            await username.click()
            await delay()
            await fill_input(username, xc_username)

            password = await page.query_selector('[name="password-input"]')
            await password.click()
            await delay()
            await fill_input(password, xc_password)

            login_button = await page.query_selector("#hotel-login-box-button")
            await login_button.click()

            element = await page.wait_for_selector(".cpt-drop-btn, .he-ctrip-hotel-title, .login-box-code-send", state='attached', timeout=5000)
            classname = await element.get_attribute("class")
            if classname.startswith("login-box-code-send"):
                print("需要验证码")
            elif classname.startswith("cpt-drop-btn"):
                print("滑动验证")
                slider = await page.query_selector('[class="image-left"]')
                slider_src = await slider.get_attribute("src")
                background_img = await page.query_selector('[class="advise"]')
                background_img_src = await background_img.get_attribute("src")
                max_loc = await get_slider_position(background_img_src.split(",")[1], slider_src.split(",")[1])
                print(max_loc)
                # 计算滑块应该移动的距离
                distance = max_loc[0]  # 假设max_loc是一个包含滑块在背景图中的位置的元组
                # 滑块按钮
                cpt_drop_btn = await page.query_selector('[class="cpt-drop-btn"]')
                # 移动滑块
                bounding_box = await cpt_drop_btn.bounding_box()
                center_x = bounding_box['x'] + 10
                center_y = bounding_box['y'] + 10
                await page.mouse.move(center_x, center_y)
                await page.mouse.down()
                await page.mouse.move(center_x + int(distance) - 5, center_y, steps=10)
                await page.mouse.up()
            if classname.startswith("he-ctrip-hotel-title") or classname.startswith("he-trip-ui-modal-header"):
                print('携程登录成功')
                cookies = await context.cookies()
                print(cookies)
        except Exception as error:
            print("错误:", error)
            classname = await element.get_attribute("class")
            if classname.startswith("login-box-code-send"):
                print("需要验证码")
        finally:
            print("当前地址是:", page.url)
            # await browser.close()


async def drag_slider(page, selector):
    element = await page.wait_for_selector(selector, timeout=5000)
    print("存在人机验证")
    bounding_box = await element.bounding_box()

    # 计算滑块的中心位置
    center_x = bounding_box['x']
    center_y = bounding_box['y']

    # 移动鼠标到滑块
    await page.mouse.move(center_x, center_y)
    await page.mouse.down()
    random_num = int(random.uniform(20, 40))
    x = int(random.uniform(108, 120))
    # 模拟滑动操作
    await page.mouse.move(center_x + x, center_y, steps=random_num)
    await asyncio.sleep(0.5)
    await page.mouse.move(center_x + x + 20, center_y, steps=10)
    await page.mouse.move(center_x + 197, center_y, steps=random_num)

    # 释放滑块
    await page.mouse.up()


async def login_mt():
    async with async_playwright() as p:
        # 开启自动化标识 让美团检查到机器操作，触发人机校验，但是这样开启的人机校验不会成功登录，纯粹为了检查滑动情况，在真实的触发中，能成功验证通过
        browser = await p.chromium.launch(headless=headless,
                                          args=args,
                                          executable_path=executable_path)
        context = await browser.new_context(user_agent=user_agent)
        old_cookies = await context.cookies()
        page = await context.new_page()

        try:
            await page.goto("https://epassport.meituan.com/new/login/account?feconfig=hotel-fe-ebooking&service=hotel&loginsource=14&noSignup=true&bg_source=4&loginurl=https%3A%2F%2Feb.meituan.com%2Febk%2Flogin%2Flogin.html&continue=https%3A%2F%2Feb.meituan.com%2Fgw%2Faccount%2Fbiz%2Fsettoken%3Fredirect_uri%3Dhttps%253A%252F%252Feb.meituan.com%252Febk%252Flogin%252Fsettoken.html")
            await asyncio.sleep(1)

            username = await page.query_selector("#account")
            await username.click()
            await asyncio.sleep(1)
            await fill_input(username, mt_username)

            password = await page.query_selector("#password")
            await password.click()
            await asyncio.sleep(1)
            await fill_input(password, mt_password)

            try:
                login_button = await page.query_selector(".new_button")
                await login_button.click()
                print("准备检查element")
                element = await page.wait_for_selector("#yodaBox, #yodaSmsCodeBtn, .page-title", timeout=5000)
                print("检查到element")
                id = await element.get_attribute("id")
                classname = await element.get_attribute("class")
                if id == "yodaBox":
                    print("存在人机验证")
                    await drag_slider(page, "#yodaBox")
                elif id == "yodaSmsCodeBtn":
                    print("存在短信验证码验证")
                    # 执行相关操作...
                if classname == 'page-title':
                    print('美团登录成功')
                    new_cookies = await context.cookies()
                    print(len(old_cookies) == len(new_cookies))
                    print(old_cookies)
                    print(new_cookies)
            except Exception as error:
                print("错误:", str(error))

        except Exception as error:
            print("错误:", str(error))
        finally:
            print("当前地址是:", page.url)
            await asyncio.sleep(2)
            # await browser.close()

asyncio.run(login_mt())
asyncio.run(login_xc())


# async def run_fn():
#     await login_mt()
#     await login_xc()


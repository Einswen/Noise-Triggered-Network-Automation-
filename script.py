import asyncio
import numpy as np
import sounddevice as sd
from playwright.async_api import async_playwright

# Audio configuration
SAMPLE_RATE = 44100
CHANNELS = 1
DB_THRESHOLD = 70  # Noise threshold in decibels
SAMPLE_DURATION = 0.5
BLOCK_DURATION = 15  # 拉黑持续时间(秒)


def calculate_decibel(audio_data):
    """Calculate decibel level from audio data"""
    rms = np.sqrt(np.mean(np.square(audio_data)))
    if rms < 1e-10:
        return 0
    return 20 * np.log10(rms / 0.00002)  # Convert to dB using reference sound pressure


async def browser_automation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. Open login page
            await page.goto("http://192.168.5.1")  # 管理后台

            # 2. Enter password and login
            password_input = page.locator('input[data-v-2681164d][type="password"]')
            await password_input.fill("xxxxxx")#路由器后台密码

            login_button = page.locator('button.loginbtn[data-v-2681164d]')
            await login_button.click()

            # 3. Click "Security" menu
            security_menu = page.locator(
                'li.el-menu-item[data-v-05e304c1] >> span:has-text("安全")'
            )
            await security_menu.click()
            await asyncio.sleep(1)  # Wait for menu transition

            # 4. Click "Anti Wi-Fi Leak" panel
            anti_wifi_leak_panel = page.locator(
                'div.el-collapse-item__header:has-text("防无线蹭网")'
            )
            await anti_wifi_leak_panel.scroll_into_view_if_needed()
            await anti_wifi_leak_panel.click(force=True)
            await asyncio.sleep(2)

            # 5. Click "New Entry" button
            add_image = page.locator(
                'img[data-v-5691bb1f][src="/jquery/static/img/table_addsymbol.svg"][class="additem"]'
            ).nth(0)
            await add_image.wait_for(state="visible", timeout=10000)
            await add_image.scroll_into_view_if_needed()
            await add_image.click(force=True)
            print("Clicked add button")

            await asyncio.sleep(1.5)

            # 6. Fill first input with "1"
            first_input = page.locator('input[type="text"][autocomplete="off"].el-input__inner').first
            await first_input.wait_for(state="visible")
            await first_input.fill("1")

            # 7. Fill MAC address
            mac_address = "08:bf:xx:xx:xx:26"  # 替换为要加入黑名单的mac地址
            mac_parts = mac_address.split(':')

            for i in range(6):
                mac_input = page.locator(f'input[tabindex="macInput{i + 1}"].el-input__inner')
                await mac_input.wait_for(state="visible", timeout=5000)
                await mac_input.click()
                await mac_input.fill(mac_parts[i].upper())
                await asyncio.sleep(0.3)

            # 8. Submit
            submit_btn = page.locator('span:has-text("提交")').nth(2)
            await submit_btn.wait_for(state="visible")
            await submit_btn.click()
            print(f"MAC地址 {mac_address} 已添加到黑名单")

            # 9. 等待设定的拉黑时间
            print(f"将在 {BLOCK_DURATION} 秒后自动删除该条目...")
            await asyncio.sleep(BLOCK_DURATION)

            # 10. 刷新页面确保条目可见
            #await page.reload()
            #await asyncio.sleep(2)

            # 重新导航到防无线蹭网面板
            #await anti_wifi_leak_panel.scroll_into_view_if_needed()
            #await anti_wifi_leak_panel.click(force=True)
           # await asyncio.sleep(2)

            # 11. 定位并点击删除按钮
            # 假设删除按钮与MAC地址在同一行，通过MAC地址定位对应行的删除按钮
            delete_button = page.locator(
                'span[data-v-7fe9c286].mobile-table-action:has-text("删除")'
            )


            await delete_button.click(force=True)
            print(f"MAC地址 {mac_address} 已从黑名单中删除")

            # 12. 确认删除（如果有确认弹窗）
            try:
                confirm_btn = page.locator('button:has-text("确认")')

                await confirm_btn.click()
                print("已确认删除")
            except:
                print("无需确认或未找到确认按钮")

            print("所有操作已成功完成")

        except Exception as e:
            print(f"操作出错: {str(e)}")
        finally:
            await asyncio.sleep(5)
            await browser.close()


async def monitor_noise_and_trigger():
    print(f"开始监测噪音... (超过 {DB_THRESHOLD} 分贝将触发操作)")
    triggered = False

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS) as stream:
            while True:
                audio_data, overflowed = stream.read(int(SAMPLE_RATE * SAMPLE_DURATION))
                if overflowed:
                    print("警告：音频缓冲区溢出，可能影响检测准确性")

                decibel = calculate_decibel(audio_data)
                print(f"当前噪音水平: {decibel:.1f} dB", end="\r")

                if decibel > DB_THRESHOLD and not triggered:
                    print(f"\n检测到超过 {DB_THRESHOLD} 分贝的噪音，开始执行操作...")
                    triggered = True
                    await browser_automation()
                    print("操作完成，继续监测噪音...")
                    triggered = False

                await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        print("\n程序已手动停止")
    except Exception as e:
        print(f"监测出错: {str(e)}")


if __name__ == "__main__":
    asyncio.run(monitor_noise_and_trigger())

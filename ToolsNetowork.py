import socket
import stun
import time

# ipv4局域网地址+ipv6地址
def get_local_ips():
    """获取本机的内网IPv4和IPv6地址
    :返回一个字典
    :ipv4和ipv6
    """
    local_ips = {"IPv4": set(), "IPv6": set()}  # 使用集合去重

    try:
        # 获取主机名
        hostname = socket.gethostname()
        # 获取所有网络接口的 IP 地址
        addrs = socket.getaddrinfo(hostname, None)

        for addr in addrs:
            # 提取 IPv4 地址
            if addr[0] == socket.AF_INET:
                ip = addr[4][0]
                if not ip.startswith("127."):  # 排除回环地址
                    local_ips["IPv4"].add(ip)
            # 提取 IPv6 地址
            elif addr[0] == socket.AF_INET6:
                ip = addr[4][0]
                if not ip.startswith("::1"):  # 排除回环地址
                    # 去掉 % 及其后面的内容
                    ip = ip.split('%')[0]
                    local_ips["IPv6"].add(ip)

        # 将集合转换为列表, 并对 IPv6 地址排序
        local_ips["IPv4"] = sorted(local_ips["IPv4"])
        # local_ips["IPv6"] = sorted(local_ips["IPv6"])
        local_ips["IPv6"] = sorted(local_ips["IPv6"], reverse=True)
        return local_ips
    except Exception as e:
        return {"error": f"无法获取本地 IP 地址: {e}"}

# NatTypeTest
def detect_nat_type(include_details=False):
    """检测NAT类型
    :param include_details: 是否返回 NAT 类型和解释, 默认为 False
    :return: 包含 external_ip 和 external_port 的字典, 如果 include_details 为 True, 则额外返回 NAT 类型和解释
    """
    nat_type, external_ip, external_port = stun.get_ip_info()

    # 默认返回值
    result = {
        "external_ip": external_ip,
        "external_port": external_port
    }

    # 如果需要返回 NAT 类型和解释
    if include_details:
        # 使用 match 语句
        match nat_type:
            case "Full Cone NAT":
                nat_type = f"NAT 类型: NAT1 ({nat_type})"
                nat_description = "外部主机可以通过公网IP和端口直接访问内网设备, 无需内网设备先发起连接。"
            case "Restricted Cone NAT":
                nat_type = f"NAT 类型: NAT2 ({nat_type})"
                nat_description = "外部主机只能通过内网设备曾经连接过的IP地址访问内网设备。"
            case "Port Restricted Cone NAT":
                nat_type = f"NAT 类型: NAT3 ({nat_type})"
                nat_description = "外部主机只能通过内网设备曾经连接过的IP地址和端口访问内网设备。"
            case "Symmetric NAT":
                nat_type = f"NAT 类型: NAT4 ({nat_type})"
                nat_description = "每个外部地址和端口都会映射到不同的内部端口, 外部主机无法通过固定的公网IP和端口访问内网设备。"
            case _:
                nat_description = "可能程序出BUG了, 或者网络访问有问题, 也有可能真检测不到"

        # 添加 NAT 类型和解释到返回值
        result.update({
            "nat_type": nat_type,
            "nat_description": nat_description
        })

    return result

# 获取公网ipv4
def get_public_ipv4(user_agent: str = None) -> str:
    """获取公网 IPv4 地址
    :param user_agent: 可选的 User-Agent, 默认为 None
    :return: 公网 IPv4 地址, 如果获取失败则返回 None
    """
    # 设置默认 User-Agent
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    try:
        # 创建 IPv4 的 TCP 套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)

        # 连接到 api.ipify.org 的 IPv4 地址
        sock.connect(('api64.ipify.org', 80))

        # 构造 HTTP 请求头
        request = (
            "GET /?format=json HTTP/1.1\r\n"
            f"Host: api64.ipify.org\r\n"
            f"User-Agent: {user_agent}\r\n"
            "Connection: close\r\n\r\n"
        ).encode('utf-8')

        # 发送 HTTP 请求
        sock.sendall(request)

        # 接收响应
        response = b""
        while True:
            data = sock.recv(4096)
            if not data:
                break
            response += data

        # 解析响应
        headers, body = response.split(b"\r\n\r\n", 1)
        public_ip = body.decode('utf-8').strip().split('"ip":"')[1].split('"')[0]
        return public_ip  # 返回公网 IPv4 地址
    except Exception:
        return None  # 获取失败, 返回 None
    finally:
        sock.close()


if __name__ == "__main__":
    start_tiem = time.time()

    def main():
        # 调用函数获取数据
        local_ips = get_local_ips()
        nat_result = detect_nat_type(include_details=True)
        public_ipv4 = get_public_ipv4()

        # 打印展示信息
        print("[网络信息展示]")
        print("-" * 30)

        # Lan
        print("[内网IP地址]")
        if "error" in local_ips:
            print(f"  错误：{local_ips['error']}")
        else:
            print(f"  内网IPv4地址: {', '.join(local_ips.get('IPv4', []))}")
            # 直接访问 IPv6 地址列表的第 0 个元素
            ipv6_addresses = local_ips.get('IPv6', [])
            if ipv6_addresses:  # 检查列表是否为空
                print(f"  内网IPv6地址: {ipv6_addresses[0]}")
            else:
                print("  内网IPv6地址: 无")

        # Wlan
        print("\n[公网地址]")
        print(f"  公网IPv4地址: {public_ipv4 if public_ipv4 else '无法获取'}")
        print("  公网IPv6地址: ",end="")
        if len(ipv6_addresses) > 1:  # 检查列表长度是否大于1
            print(ipv6_addresses[1])
        else:
            print("无法获取")

        # Nat
        print("\n[NAT类型检测]")
        if "error" in nat_result:
            print(f"  错误：{nat_result['error']}")
        else:
            print(f"  外部IP: {nat_result.get('external_ip', '未知')}")
            print(f"  外部端口: {nat_result.get('external_port', '未知')}")
            print(f"  NAT类型: {nat_result.get('nat_type', '未知')}")
            print(f"  NAT描述: {nat_result.get('nat_description', '未知')}")

    main()

    end_time = time.time()
    elapsed_time = end_time - start_tiem
    print(f"完成用时：{elapsed_time:.6f} 秒")

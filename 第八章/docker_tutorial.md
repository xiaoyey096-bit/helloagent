# Docker 完整命令教程

> 为第八章本地数据库(Qdrant + Neo4j)而写,但命令通用。
> 约定:`<>` 表示必填参数,`[]` 表示可选参数。

---

## 一、镜像管理(安装包层面)

```powershell
# 搜索镜像(看有哪些版本、哪个最流行)
docker search qdrant

# 拉取镜像(不写 tag 默认 :latest)
docker pull neo4j:5              # 拉取指定版本
docker pull qdrant/qdrant        # 拉取最新版
docker pull -a neo4j             # ⚠️ 拉取所有版本(几乎不会用到)

# 查看本地已有哪些镜像
docker images                    # 完整列表
docker images neo4j              # 只看某个镜像
docker image ls -q               # 只显示镜像 ID(配合批量删除)

# 查看镜像详情
docker inspect neo4j:5            # JSON 格式的全部元数据(入口命令、环境变量、暴露端口等)

# 查看镜像构建历史(每一层多大、执行了什么)
docker history neo4j:5

# 给镜像打标签(重命名/标记版本)
docker tag neo4j:5 myneo4j:v1     # 相当于复制一个别名,两个 tag 指向同一镜像

# 删除镜像(必须先删掉用它的容器)
docker rmi neo4j:4.4              # 删除指定镜像
docker rmi -f neo4j:4.4           # 强制删除(容器在用时会连容器一起强删,慎用)
docker rmi myneo4j:v1             # 删除 tag(若还有别的 tag 指向它,只删名字不删镜像)

# 导出 / 导入镜像(离线拷贝给别人的场景)
docker save -o neo4j5.tar neo4j:5       # 把镜像打包成文件
docker load -i neo4j5.tar               # 从文件恢复镜像

# 清理悬空镜像(build/拉取过程中产生的无名中间层,<tag=none>)
docker image prune               # 删除所有悬空镜像
docker image prune -a            # ⚠️ 删除所有未被容器使用的镜像(回收大量空间,但下次要重拉)
```

---

## 二、容器管理(运行实例层面)

### 2.1 创建并启动

```powershell
# docker run 的完整常用形态(以 Neo4j 为例)
docker run -d \                          # -d 后台运行(detached)
  --name hello-agents-neo4j \            # 给容器起名(不写则随机生成名字)
  -p 7474:7474 -p 7687:7687 \            # 端口映射: 宿主机端口:容器端口
  -e NEO4J_AUTH=neo4j/hello-agents-2026 \ # -e 注入环境变量
  -v neo4j_data:/data \                  # -v 命名卷:容器目录(数据持久化)
  --restart unless-stopped \             # 开机/崩溃后自动重启策略
  neo4j:5                                # 镜像名(最后写)

# 前台运行(日志直接打印,Ctrl+C 停止,调试用)
docker run --rm -it ubuntu bash          # --rm 退出即删容器;-i 交互;-t 分配终端

# 在已运行的容器里执行命令
docker exec -it hello-agents-neo4j bash        # 进容器开 shell(exit 退出,容器继续跑)
docker exec hello-agents-qdrant ls /qdrant/storage   # 不进 shell 直接执行命令
```

### 2.2 查看状态

```powershell
docker ps                        # 查看运行中的容器
docker ps -a                     # 包含已退出的(查"我的容器怎么没了"必用)
docker ps -aq                    # 只显示容器 ID
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"   # 自定义显示列

docker inspect hello-agents-neo4j          # 容器全部元数据(IP、挂载、日志路径)
docker inspect -f '{{.State.Status}}' hello-agents-neo4j   # 只提取某个字段

docker logs hello-agents-qdrant             # 查看全部日志
docker logs -f hello-agents-qdrant          # 实时跟踪(类似 tail -f,Ctrl+C 退出查看)
docker logs --tail 100 hello-agents-neo4j   # 只看最后 100 行
docker logs -t hello-agents-neo4j           # 带时间戳

docker stats                              # 所有容器实时资源占用(CPU/内存/网络)
docker stats hello-agents-neo4j            # 只看一个

docker top hello-agents-neo4j              # 看容器内跑了哪些进程
docker port hello-agents-neo4j             # 看端口映射关系
```

### 2.3 生命周期控制

```powershell
docker start hello-agents-neo4j    # 启动已停止的容器
docker stop hello-agents-neo4j     # 优雅停止(先发 SIGTERM,10 秒后强杀)
docker stop -t 3 hello-agents-neo4j # 只等 3 秒
docker kill hello-agents-neo4j     # 立即强杀(SIGKILL)
docker restart hello-agents-neo4j  # 重启

# 暂停/恢复(不停止进程,只冻结)
docker pause hello-agents-neo4j
docker unpause hello-agents-neo4j

# 删除容器(必须先 stop)
docker rm hello-agents-neo4j               # 删除已停止的容器
docker rm -f hello-agents-neo4j            # 强制(运行中也直接删)
docker rm $(docker ps -aq)                 # ⚠️ 删除所有容器(含退出的)
docker container prune                     # 删除所有已退出的容器(比较安全)

# 从容器复制文件(双向)
docker cp hello-agents-neo4j:/logs/debug.log ./        # 容器 → 本机
docker cp ./config.conf hello-agents-neo4j:/etc/       # 本机 → 容器
```

### 2.4 容器与镜像互转(调试快照)

```powershell
docker commit hello-agents-neo4j mysnapshot:v1   # 把容器当前状态固化为新镜像
docker export hello-agents-neo4j > box.tar       # 导出容器文件系统
docker import box.tar box:v1                     # 导入为镜像
```

---

## 三、数据卷管理(数据持久化)

```powershell
docker volume ls                          # 列出所有卷
docker volume inspect hello-agents-chapter8_qdrant_data   # 卷详情(实际存储路径、大小)
docker volume create mydata               # 手动创建卷
docker volume rm hello-agents-chapter8_neo4j_logs        # 删除指定卷(没容器在用才行)
docker volume prune                       # ⚠️ 删除所有未被使用的卷(数据会丢!)

# 挂载方式对比(docker run 的 -v 参数):
#   -v mydata:/data              命名卷(Docker 管理,推荐存数据)
#   -v E:/mydir:/data            绑定挂载(直接映射本机目录,改代码/配置常用)
#   -v /data                     匿名卷(不推荐,难管理)
```

---

## 四、网络管理

```powershell
docker network ls                          # 列出网络(默认有 bridge/host/none)
docker network inspect bridge              # 看网络里有哪些容器、各自 IP
docker network create mynet                # 创建自定义网络
docker run -d --network mynet --name db neo4j:5     # 加入自定义网络

# 同一自定义网络内容器可用名字互访(内置 DNS):
#   容器 qdrant 里的应用直接访问 http://neo4j:7474,不用写 IP
docker network rm mynet                    # 删除网络
docker network prune                       # 清理无用网络
```

> 本章场景:Python 在宿主机,通过 `localhost:6333` / `bolt://localhost:7687` 访问,
> 走的是 `-p` 端口映射;容器互相访问才需要自定义网络。

---

## 五、Docker Compose(多容器编排,本章主用)

```powershell
docker compose up                  # 前台启动(看日志,Ctrl+C 停止)
docker compose up -d               # 后台启动
docker compose up -d --build       # 有 build 段时重新构建镜像再启动
docker compose up -d neo4j         # 只启动其中一个服务

docker compose ps                  # 本项目的容器状态
docker compose logs                # 本项目所有服务日志
docker compose logs -f qdrant      # 跟踪某个服务

docker compose restart             # 重启所有服务
docker compose restart neo4j       # 重启一个
docker compose stop                # 停止(容器保留,可 start 回来)
docker compose start               # 启动已停止的
docker compose down                # 停止并删除容器+网络(卷保留)
docker compose down -v             # ⚠️ 连卷一起删 = 数据全没
docker compose down --rmi all      # 连镜像一起删

docker compose exec neo4j bash     # 进入某个服务容器(等同 docker exec)
docker compose pull                # 提前拉取 compose 里定义的镜像
docker compose config              # 检查/查看最终生效的配置
```

> 教学提示:compose 本质是把 `docker run` 的一长串参数写进了 YAML。
> 对照着看 [docker-compose.yml](docker-compose.yml) 里的 `ports`/`environment`/`volumes`
> 与 2.1 节的 `-p`/`-e`/`-v`,一一对应。

---

## 六、清理空间(老玩家必备)

```powershell
docker system df                # 总览:镜像/容器/卷/缓存各占多少空间
docker system prune             # 一键清理:停止的容器+悬空镜像+无用网络+构建缓存
docker system prune -a          # ⚠️ 激进版:连未使用的镜像也删
docker system prune --volumes   # ⚠️ 连无用卷也删
```

---

## 七、本章场景速查卡

| 想做什么           | 命令                                                     |
| ------------------ | -------------------------------------------------------- |
| 启动两个数据库     | `docker compose up -d`                                 |
| 看跑没跑起来       | `docker compose ps`                                    |
| 看 Neo4j 日志      | `docker compose logs -f neo4j`                         |
| 重启 Neo4j         | `docker compose restart neo4j`                         |
| 进 Neo4j 容器      | `docker compose exec neo4j bash`                       |
| 彻底清空重来       | `docker compose down -v` 再 `docker compose up -d`   |
| 看数据占了多少空间 | `docker system df`                                     |
| Qdrant 控制台      | 浏览器 http://localhost:6333/dashboard                   |
| Neo4j 浏览器       | 浏览器 http://localhost:7474 (neo4j / hello-agents-2026) |

---

## 八、常见坑(都是本机踩过的)

1. **中文目录名** → compose 项目名变空串报错,用 `name:` 显式指定
2. **`unexpected EOF`** → 拉镜像网络断了,重试即可;国内可配镜像加速器(Docker Desktop → Settings → Docker Engine 里加 `registry-mirrors`)
3. **`port is already allocated`** → 端口被占:旧容器(哪怕退出的占名容器)或本机服务占用,`docker ps -a` + `netstat -ano | findstr 6333` 排查
4. **删容器 ≠ 删数据** → 数据在卷里;想让记忆"失忆"要 `down -v` 或删卷
5. **`docker rmi` 报 "image is being used"** → 先 `docker rm` 用它的容器

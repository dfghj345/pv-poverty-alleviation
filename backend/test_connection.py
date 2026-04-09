import asyncio
from datetime import date
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_GeomFromText, ST_AsText, ST_Distance
from app.db.session import AsyncSessionLocal, engine
from app.models.project import Base, Project, Policy
from sqlalchemy import cast
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import insert

from backend.app.db import session

async def test_database_integration():
    print("🔍 开始数据库集成测试...")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 检查数据库连接与 PostGIS 版本
            result = await session.execute(text("SELECT postgis_full_version();"))
            version = result.scalar()
            print(f"✅ 数据库连接成功! PostGIS 版本: {version[:50]}...")

            # 2. 准备测试数据：电价政策
            # 使用 merge 防止重复运行脚本时报错
            beijing_policy = Policy(
                province="北京",
                electricity_price=0.3598,
                subsidy_standard=0.0
            )
            session.add(beijing_policy)
            await session.flush() # 获取 policy.id

            # 3. 准备测试数据：光伏电站 (使用 WGS84 坐标: 经度 116.4, 纬度 39.9)
            # ST_GeomFromText 将字符串转为 PostGIS 几何对象
            test_project = Project(
                name="测试光伏扶贫电站-01",
                capacity=500.0,
                commissioning_date=date(2026, 3, 1),
                location=ST_GeomFromText('POINT(116.40 39.90)', srid=4326),
                policy_id=beijing_policy.id
            )
            session.add(test_project)
            await session.commit()
            print("✅ 测试数据（Policy & Project）插入成功!")
            
            # 即使“北京”存在，也只是更新电价，不会报错
            stmt = insert(Policy).values(province="北京", electricity_price=0.3598)
            stmt = stmt.on_conflict_do_update(
            index_elements=['province'],
                set_={"electricity_price": 0.3598}
            )
            await session.execute(stmt)

            # 4. 空间查询验证：查找距离天安门 (116.39, 39.90) 10公里内的电站
            # 注意：4326 是经纬度坐标系，计算距离需注意单位转换，此处仅验证函数可用性
            query = select(Project.name).where(
                ST_Distance(
                    cast(Project.location, Geography), # 强制转为地理信息类型
                     cast(ST_GeomFromText('POINT(116.39 39.90)', 4326), Geography)
                 ) < 5000 # 这里就是实打实的 5000 米
            )
            
            result = await session.execute(query)
            row = result.first()
            if row:
                print(f"✅ 空间查询成功! 找到电站: {row[0]}, 坐标: {row[1]}")
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
            await session.rollback()
        finally:
            await session.close()

# ... 前面的 import 和函数定义保持不变 ...

async def main():
    """统一管理所有异步测试步骤"""
    print("🚀 开始执行集成测试任务流水线...")
    
    # 1. 初始化数据库环境 (只在同一个 loop 中执行一次)
    async with engine.begin() as conn:
        print("🛠️ 正在检查并创建 PostGIS 扩展及表结构...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. 执行核心业务逻辑测试
    await test_database_integration()
    
    print("🏁 所有测试步骤执行完毕。")

if __name__ == "__main__":
    # 核心：只调用一次 asyncio.run
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"💥 运行过程中出现未捕获异常: {e}")
#!/usr/bin/env python3
"""
Redis Database Cleanup Script for MarkUI Backend

This script provides options to clean up Redis data:
1. Complete database flush (start fresh)
2. Clean only PDF documents
3. Clean only conversion jobs
4. Clean only user settings
5. Clean expired keys only

Usage:
    python scripts/cleanup_redis.py --all              # Clean everything
    python scripts/cleanup_redis.py --pdfs             # Clean only PDFs
    python scripts/cleanup_redis.py --jobs             # Clean only conversion jobs
    python scripts/cleanup_redis.py --settings         # Clean only user settings
    python scripts/cleanup_redis.py --expired          # Clean only expired keys
    python scripts/cleanup_redis.py --interactive      # Interactive mode
"""

import asyncio
import argparse
import sys
import os
from typing import List, Dict, Any
import logging

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

try:
    import redis.asyncio as redis
except ImportError:
    print("❌ Redis package not installed. Please install it with: pip install redis")
    sys.exit(1)

from core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RedisCleanup:
    """Redis cleanup utility"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {self.settings.redis_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("🔌 Disconnected from Redis")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get current database statistics"""
        try:
            # Get all keys
            all_keys = await self.redis_client.keys("*")
            
            # Categorize keys
            pdf_keys = [k for k in all_keys if k.startswith("pdf:")]
            job_keys = [k for k in all_keys if k.startswith("job:")]
            counter_keys = [k for k in all_keys if k.startswith("counter:")]
            settings_keys = [k for k in all_keys if k.startswith("settings:")]
            other_keys = [k for k in all_keys if not any(k.startswith(prefix) for prefix in ["pdf:", "job:", "counter:", "settings:"])]
            
            # Get memory usage
            memory_info = await self.redis_client.info("memory")
            used_memory = memory_info.get("used_memory_human", "Unknown")
            
            return {
                "total_keys": len(all_keys),
                "pdf_documents": len(pdf_keys),
                "conversion_jobs": len(job_keys),
                "counters": len(counter_keys),
                "user_settings": len(settings_keys),
                "other_keys": len(other_keys),
                "memory_usage": used_memory,
                "categories": {
                    "pdf_keys": pdf_keys[:10],  # Show first 10 as examples
                    "job_keys": job_keys[:10],
                    "counter_keys": counter_keys,
                    "settings_keys": settings_keys,
                    "other_keys": other_keys[:10]
                }
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def cleanup_all(self) -> bool:
        """Clean up entire Redis database"""
        try:
            logger.warning("🧹 Starting complete database cleanup...")
            await self.redis_client.flushdb()
            logger.info("✅ Complete database cleanup completed")
            return True
        except Exception as e:
            logger.error(f"❌ Error during complete cleanup: {e}")
            return False
    
    async def cleanup_pdfs(self) -> int:
        """Clean up only PDF documents"""
        try:
            logger.info("🧹 Starting PDF cleanup...")
            pdf_keys = await self.redis_client.keys("pdf:*")
            
            if not pdf_keys:
                logger.info("ℹ️  No PDF documents found")
                return 0
            
            deleted_count = await self.redis_client.delete(*pdf_keys)
            logger.info(f"✅ Deleted {deleted_count} PDF documents")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error during PDF cleanup: {e}")
            return 0
    
    async def cleanup_jobs(self) -> int:
        """Clean up only conversion jobs"""
        try:
            logger.info("🧹 Starting conversion jobs cleanup...")
            job_keys = await self.redis_client.keys("job:*")
            jobs_list_keys = await self.redis_client.keys("jobs:*")
            
            all_job_keys = job_keys + jobs_list_keys
            
            if not all_job_keys:
                logger.info("ℹ️  No conversion jobs found")
                return 0
            
            deleted_count = await self.redis_client.delete(*all_job_keys)
            logger.info(f"✅ Deleted {deleted_count} conversion job entries")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error during jobs cleanup: {e}")
            return 0
    
    async def cleanup_settings(self) -> int:
        """Clean up only user settings"""
        try:
            logger.info("🧹 Starting user settings cleanup...")
            settings_keys = await self.redis_client.keys("settings:*")
            
            if not settings_keys:
                logger.info("ℹ️  No user settings found")
                return 0
            
            deleted_count = await self.redis_client.delete(*settings_keys)
            logger.info(f"✅ Deleted {deleted_count} user settings entries")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error during settings cleanup: {e}")
            return 0
    
    async def cleanup_counters(self) -> int:
        """Clean up ID counters"""
        try:
            logger.info("🧹 Starting counters cleanup...")
            counter_keys = await self.redis_client.keys("counter:*")
            
            if not counter_keys:
                logger.info("ℹ️  No counters found")
                return 0
            
            deleted_count = await self.redis_client.delete(*counter_keys)
            logger.info(f"✅ Deleted {deleted_count} counter entries")
            return deleted_count
        except Exception as e:
            logger.error(f"❌ Error during counters cleanup: {e}")
            return 0
    
    async def cleanup_expired(self) -> int:
        """Clean up only expired keys"""
        try:
            logger.info("🧹 Starting expired keys cleanup...")
            all_keys = await self.redis_client.keys("*")
            expired_count = 0
            
            for key in all_keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1
                elif ttl == 0:  # Key expired but not yet removed
                    await self.redis_client.delete(key)
                    expired_count += 1
            
            logger.info(f"✅ Cleaned up {expired_count} expired keys")
            return expired_count
        except Exception as e:
            logger.error(f"❌ Error during expired keys cleanup: {e}")
            return 0
    
    async def interactive_cleanup(self):
        """Interactive cleanup mode"""
        print("\n" + "="*60)
        print("🧹 REDIS INTERACTIVE CLEANUP")
        print("="*60)
        
        # Show current stats
        stats = await self.get_database_stats()
        if stats:
            print(f"\n📊 Current Database Statistics:")
            print(f"   Total Keys: {stats['total_keys']}")
            print(f"   PDF Documents: {stats['pdf_documents']}")
            print(f"   Conversion Jobs: {stats['conversion_jobs']}")
            print(f"   User Settings: {stats['user_settings']}")
            print(f"   Counters: {stats['counters']}")
            print(f"   Other Keys: {stats['other_keys']}")
            print(f"   Memory Usage: {stats['memory_usage']}")
        
        if stats['total_keys'] == 0:
            print("\n✨ Database is already empty!")
            return
        
        print(f"\n🎯 Cleanup Options:")
        print(f"   1. Clean everything (COMPLETE RESET)")
        print(f"   2. Clean PDF documents only ({stats['pdf_documents']} items)")
        print(f"   3. Clean conversion jobs only ({stats['conversion_jobs']} items)")
        print(f"   4. Clean user settings only ({stats['user_settings']} items)")
        print(f"   5. Clean counters only ({stats['counters']} items)")
        print(f"   6. Clean expired keys only")
        print(f"   7. Show detailed key information")
        print(f"   0. Exit without changes")
        
        while True:
            try:
                choice = input(f"\n👉 Enter your choice (0-7): ").strip()
                
                if choice == "0":
                    print("👋 Exiting without changes")
                    return
                elif choice == "1":
                    confirm = input("⚠️  This will DELETE ALL DATA! Type 'YES' to confirm: ")
                    if confirm == "YES":
                        await self.cleanup_all()
                    else:
                        print("❌ Cleanup cancelled")
                elif choice == "2":
                    await self.cleanup_pdfs()
                elif choice == "3":
                    await self.cleanup_jobs()
                elif choice == "4":
                    await self.cleanup_settings()
                elif choice == "5":
                    await self.cleanup_counters()
                elif choice == "6":
                    await self.cleanup_expired()
                elif choice == "7":
                    await self.show_detailed_info(stats)
                    continue
                else:
                    print("❌ Invalid choice. Please enter 0-7.")
                    continue
                
                # Show updated stats after cleanup
                print("\n📊 Updated Statistics:")
                new_stats = await self.get_database_stats()
                if new_stats:
                    print(f"   Total Keys: {new_stats['total_keys']}")
                    print(f"   Memory Usage: {new_stats['memory_usage']}")
                
                break
                
            except KeyboardInterrupt:
                print("\n\n👋 Cleanup cancelled by user")
                return
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def show_detailed_info(self, stats: Dict[str, Any]):
        """Show detailed information about keys"""
        print(f"\n📋 Detailed Key Information:")
        print(f"-" * 40)
        
        categories = stats.get("categories", {})
        
        for category, keys in categories.items():
            if keys:
                print(f"\n{category.replace('_', ' ').title()}:")
                for key in keys:
                    try:
                        key_type = await self.redis_client.type(key)
                        ttl = await self.redis_client.ttl(key)
                        ttl_str = f"TTL: {ttl}s" if ttl > 0 else "No expiry" if ttl == -1 else "Expired"
                        print(f"  • {key} ({key_type}) - {ttl_str}")
                    except Exception as e:
                        print(f"  • {key} - Error: {e}")
                
                if len(keys) == 10 and category in ["pdf_keys", "job_keys", "other_keys"]:
                    total_count = stats.get(category.replace("_keys", "s").replace("other", "other_keys"), 0)
                    if total_count > 10:
                        print(f"  ... and {total_count - 10} more")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Redis Database Cleanup Script for MarkUI Backend")
    parser.add_argument("--all", action="store_true", help="Clean everything (complete reset)")
    parser.add_argument("--pdfs", action="store_true", help="Clean only PDF documents")
    parser.add_argument("--jobs", action="store_true", help="Clean only conversion jobs")
    parser.add_argument("--settings", action="store_true", help="Clean only user settings")
    parser.add_argument("--counters", action="store_true", help="Clean only ID counters")
    parser.add_argument("--expired", action="store_true", help="Clean only expired keys")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--stats", action="store_true", help="Show database statistics only")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    
    args = parser.parse_args()
    
    # If no arguments provided, default to interactive mode
    if not any(vars(args).values()):
        args.interactive = True
    
    cleanup = RedisCleanup()
    
    try:
        # Connect to Redis
        if not await cleanup.connect():
            sys.exit(1)
        
        # Show stats only
        if args.stats:
            stats = await cleanup.get_database_stats()
            if stats:
                print(f"\n📊 Redis Database Statistics:")
                print(f"   Total Keys: {stats['total_keys']}")
                print(f"   PDF Documents: {stats['pdf_documents']}")
                print(f"   Conversion Jobs: {stats['conversion_jobs']}")
                print(f"   User Settings: {stats['user_settings']}")
                print(f"   Counters: {stats['counters']}")
                print(f"   Other Keys: {stats['other_keys']}")
                print(f"   Memory Usage: {stats['memory_usage']}")
            return
        
        # Interactive mode
        if args.interactive:
            await cleanup.interactive_cleanup()
            return
        
        # Confirmation for destructive operations
        if not args.force:
            if args.all:
                confirm = input("⚠️  This will DELETE ALL DATA! Type 'YES' to confirm: ")
                if confirm != "YES":
                    print("❌ Cleanup cancelled")
                    return
            else:
                confirm = input("⚠️  This will delete selected data. Continue? (y/N): ")
                if confirm.lower() not in ['y', 'yes']:
                    print("❌ Cleanup cancelled")
                    return
        
        # Execute cleanup operations
        if args.all:
            await cleanup.cleanup_all()
        elif args.pdfs:
            await cleanup.cleanup_pdfs()
        elif args.jobs:
            await cleanup.cleanup_jobs()
        elif args.settings:
            await cleanup.cleanup_settings()
        elif args.counters:
            await cleanup.cleanup_counters()
        elif args.expired:
            await cleanup.cleanup_expired()
        
        print("✅ Cleanup completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Cleanup cancelled by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        await cleanup.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 
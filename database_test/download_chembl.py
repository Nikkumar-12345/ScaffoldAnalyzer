import os
import tarfile
import shutil
import chembl_downloader


print("=" * 70)
print("ChEMBL 37 SQLITE DOWNLOAD")
print("=" * 70)


try:

    print("\nStep 1: Downloading archive...")
    print("This may take a while. Please do not stop the script.\n")

    archive_path = chembl_downloader.download_sqlite(
        version="37"
    )

    print("\nArchive downloaded:")
    print(archive_path)

    print("\nStep 2: Checking archive integrity...")

    with tarfile.open(
        archive_path,
        "r:gz"
    ) as tar:

        bad_member = tar.getmember(
            "chembl_37/chembl_37.db"
        ) if False else None

        # Force Python to read through the archive metadata
        members = tar.getmembers()

        print(f"\nArchive is readable.")
        print(f"Files inside archive: {len(members)}")

        print("\nContents:")

        for member in members:
            print(member.name)

    archive_size = os.path.getsize(
        archive_path
    ) / (1024 ** 3)

    print(
        f"\nCompressed archive size: "
        f"{archive_size:.2f} GB"
    )


except Exception as e:

    print("\n" + "=" * 70)
    print("DOWNLOAD / ARCHIVE CHECK FAILED")
    print("=" * 70)

    print(f"\n{type(e).__name__}: {e}")

    raise


print("\n" + "=" * 70)
print("SUCCESS")
print("=" * 70)

disk = shutil.disk_usage(
    os.path.dirname(archive_path)
)

print(
    f"\nFree disk space: "
    f"{disk.free / (1024 ** 3):.2f} GB"
)
from django.db import migrations

# The one agreed size list. Values are what Item.size stores; labels are what people see.
# Recreated in display order, because overview and filter chips order sizes by id.
SIZES = {
    "clothing": [(v, v) for v in ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]],
    "trousers": [(str(w), f"W{w}") for w in range(28, 43)],
    "shoes": [(str(s), f"UK {s}") for s in range(3, 14)],
}


def set_sizes(apps, schema_editor):
    SizeOption = apps.get_model("inventory", "SizeOption")
    SizeOption.objects.all().delete()
    for size_type, options in SIZES.items():
        for value, label in options:
            SizeOption.objects.create(size_type=size_type, value=value, label=label)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0013_activitylog"),
    ]

    operations = [
        migrations.RunPython(set_sizes, migrations.RunPython.noop),
    ]

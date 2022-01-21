# Generated by Django 3.1.12 on 2021-07-07 20:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('botapp', '0010_auto_20210707_1736'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('use_tag', models.BooleanField(default=True)),
            ],
        ),
    ]
# Generated by Django 4.1.10 on 2023-12-05 07:02

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terminal', '0067_alter_replaystorage_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppProvider',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, unique=True, verbose_name='Name')),
                ('hostname', models.CharField(max_length=128, verbose_name='Hostname')),
            ],
            options={
                'ordering': ('-date_created',),
            },
        ),
        migrations.CreateModel(
            name='VirtualApp',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.SlugField(max_length=128, unique=True, verbose_name='Name')),
                ('display_name', models.CharField(max_length=128, verbose_name='Display name')),
                ('version', models.CharField(max_length=16, verbose_name='Version')),
                ('author', models.CharField(max_length=128, verbose_name='Author')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is active')),
                ('protocols', models.JSONField(default=list, verbose_name='Protocol')),
                ('image_name', models.CharField(max_length=128, verbose_name='Image name')),
                ('image_protocol', models.CharField(default='vnc', max_length=16, verbose_name='Image protocol')),
                ('image_port', models.IntegerField(default=5900, verbose_name='Image port')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('tags', models.JSONField(default=list, verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Virtual app',
            },
        ),
        migrations.AlterField(
            model_name='terminal',
            name='type',
            field=models.CharField(choices=[('koko', 'KoKo'), ('guacamole', 'Guacamole'), ('omnidb', 'OmniDB'), ('xrdp', 'Xrdp'), ('lion', 'Lion'), ('core', 'Core'), ('celery', 'Celery'), ('magnus', 'Magnus'), ('razor', 'Razor'), ('tinker', 'Tinker'), ('video_worker', 'Video Worker'), ('chen', 'Chen'), ('kael', 'Kael'), ('panda', 'Panda')], default='koko', max_length=64, verbose_name='type'),
        ),
        migrations.CreateModel(
            name='VirtualAppPublication',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('status', models.CharField(default='pending', max_length=16, verbose_name='Status')),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='publications', to='terminal.virtualapp', verbose_name='Virtual app')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='publications', to='terminal.appprovider', verbose_name='App Provider')),
            ],
            options={
                'verbose_name': 'Virtual app publication',
                'unique_together': {('provider', 'app')},
            },
        ),
        migrations.AddField(
            model_name='virtualapp',
            name='providers',
            field=models.ManyToManyField(through='terminal.VirtualAppPublication', to='terminal.appprovider', verbose_name='Providers'),
        ),
        migrations.AddField(
            model_name='appprovider',
            name='apps',
            field=models.ManyToManyField(through='terminal.VirtualAppPublication', to='terminal.virtualapp', verbose_name='Virtual app'),
        ),
        migrations.AddField(
            model_name='appprovider',
            name='terminal',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='app_provider', to='terminal.terminal', verbose_name='Terminal'),
        ),
    ]
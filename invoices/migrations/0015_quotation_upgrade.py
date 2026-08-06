import django.db.models.deletion
import datetime
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0014_alter_product_minimum_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quotation',
            name='quote_no',
        ),
        migrations.AddField(
            model_name='quotation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='quotation',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotation',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='quotation',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='invoices.organization'),
        ),
        migrations.AddField(
            model_name='quotation',
            name='quotation_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.AddField(
            model_name='quotation',
            name='quotation_no',
            field=models.CharField(default='QTN-0000', max_length=50, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='quotation',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='quotation',
            name='terms',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='quotation',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='quotation',
            name='valid_until',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='quotation',
            name='vat',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('SENT', 'Sent'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('EXPIRED', 'Expired'), ('CONVERTED', 'Converted')], default='DRAFT', max_length=20),
        ),
        migrations.AlterField(
            model_name='quotation',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.CreateModel(
            name='QuotationItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('qty', models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ('unit_price', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoices.product')),
                ('quotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='invoices.quotation')),
            ],
        ),
    ]

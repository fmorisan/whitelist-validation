from rest_framework import serializers
import rest_framework
from rest_framework.exceptions import ValidationError
from web3 import Web3
from eth_account.messages import encode_defunct

from .models import (
    NFT,
    Whitelist,
    Signature,
    Signer
)

web3 = Web3()

class WhitelistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Whitelist
        fields = "__all__"


class NFTSerializer(serializers.ModelSerializer):
    whitelist = WhitelistSerializer()
    class Meta:
        model = NFT
        fields = '__all__'


class NFTCreationSerializer(serializers.Serializer):
    whitelist = WhitelistSerializer()
    contract_address = serializers.CharField()
    token_id = serializers.IntegerField()

    def create(self, validated_data):
        whitelist = Whitelist.objects.create(
            **validated_data.pop('whitelist')
        )
        nft = NFT.objects.create(
            whitelist=whitelist,
            contract_address=validated_data['contract_address'],
            token_id=validated_data['token_id']
        )
        return nft

class SignatureSerializer(serializers.ModelSerializer):
    signature = serializers.CharField()
    signer = serializers.CharField()

    def validate(self, data):
        signature = data.pop('signature')
        whitelist = data.pop('whitelist')
        print(f"got data {signature}... {whitelist}")

        if whitelist.signature_set.filter(signer__address=data['signer']).exists():
            raise serializers.ValidationError(f"Signer {data['signer']} has already signed this whitelist")

        whitelist_file = encode_defunct(
            b"\n".join(whitelist.whitelist_file.readlines())
        )

        try:
            signer = web3.eth.account.recover_message(whitelist_file, signature=signature)
        except Exception as exc:
            raise ValidationError(exc)

        if data.pop('signer') != signer:
            raise ValidationError("Signature does not match signer's address")
        
        if not Signer.objects.filter(address=signer).exists():
            raise ValidationError(f"Signer ${signer} not registered")

        return {
            "whitelist": whitelist,
            "signature": signature,
            "signer": Signer.objects.get(address=signer)
        }

    class Meta:
        model = Signature
        fields = (
            'whitelist',
            'signature',
            'signer'
        )